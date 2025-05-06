from functools import lru_cache
from flask import Flask, render_template, send_from_directory, request, abort, jsonify, redirect, url_for
import os
import json
import re
import subprocess
import socket
from typing import Tuple
from threading import Thread, Lock
from urllib.parse import unquote
from config import root_dir, json_path, scriptPath, pythonExe, app_host, app_port

app = Flask(__name__)

# 共享输出缓冲区和进程控制
output_buffer = []
buffer_lock = Lock()
current_process = None
url_pattern = re.compile(r'^(https?|ftp)://[^\s/$.?#].[^\s]*$')


def load_data():
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


@lru_cache(maxsize=3000)
def image_exists(id):
    """检查static/images目录下是否存在对应的图片文件"""
    image_path = os.path.join(app.static_folder, 'images', f"{id}.webp")
    return os.path.exists(image_path)


@app.route('/')
def index():
    data = load_data()
    entries = []
    for category in data['data'].values():
        for entry in category:
            entry_id = entry['id']
            entries.append({
                'prefix': entry['prefix'],
                'title': entry.get('title', 'undefined'),
                'relative_path': entry['relative_path'].replace('\\', '/'),
                'image_url': f"/static/images/{entry_id}.webp" if image_exists(entry_id) else None
            })

    page = request.args.get('page', 1, type=int)
    per_page = 100
    total = len(entries)
    start = (page - 1) * per_page
    end = start + per_page
    return render_template('index.html',
                           entries=entries[start:end],
                           page=page,
                           total_pages=(total + per_page - 1) // per_page,
                           category_code=None)


@app.route('/view/<path:relative_path>')
def view_folder(relative_path):
    full_path = os.path.join(root_dir, unquote(relative_path))
    if not os.path.exists(full_path):
        return "Path not found", 404

    images = []
    files = sorted(os.listdir(full_path),
                   key=lambda x: int(re.findall(r'^\d+', x)[0]) if re.findall(r'^\d+', x) else 0)
    for f in files:
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp')):
            images.append({'name': f, 'url': f"/original/{relative_path}/{f}"})

    return render_template('viewer.html', images=images, folder_path=relative_path)


@app.route('/original/<path:filepath>')
def serve_original(filepath):
    return send_from_directory(root_dir, unquote(filepath))


# 控制台相关路由
@app.route('/console')
def console():
    return render_template('console.html')


@app.route('/console/start', methods=['POST'])
def start_task():
    global current_process
    data = request.get_json()

    if current_process and current_process.poll() is None:
        return jsonify({'error': 'A task is already running'}), 400

    commands = []
    choice1 = data.get('choice1')
    choice2 = data.get('choice2')
    url = data.get('url', '')

    # 验证URL格式
    if choice2 == '4':
        if not url_pattern.match(url):
            return jsonify({'error': 'Invalid URL format'}), 400

    # 命令构建
    try:
        commands = []

        if choice1 == '1':
            # 第一阶段：获取ID
            base_scripts = [
                'get_id_new.py',
                'handing.py',
                'download.py',
            ]

            # 根据选择添加参数
            if choice2 == '1':
                url_param = 'https://nhentai.net/search/?q=pages%3A%3E60+uncensored+%5Bchinese%5D&page='
            elif choice2 == '3':
                url_param = 'https://nhentai.net/search/?q=pages%3A%3E100+%5Bchinese%5D&page='
            elif choice2 == '4':
                url_param = url  # 用户输入的URL

            # 构建基础命令
            for s in base_scripts:
                cmd = [pythonExe, '-u', os.path.join(scriptPath, s)]
                if s == 'get_id_new.py' and choice2 in ['1', '3', '4']:
                    cmd.append(url_param)
                commands.append(cmd)

            # # 第二阶段：自动分类
            # 这里取决与用户是否决定要开启自动分类，默认启动应用时会检测是否获取封面图片
            # commands.append([pythonExe, os.path.join(scriptPath, 'classify.py')])

        elif choice1 == '2':
            # 继续下载模式
            commands = [
                [pythonExe, os.path.join(scriptPath, 'download.py')],
                # [pythonExe, os.path.join(scriptPath, 'classify.py')]
            ]

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    # 启动异步任务
    def run_commands():
        global output_buffer, current_process
        with buffer_lock:
            output_buffer.clear()

        for cmd in commands:
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',
                    cwd=scriptPath,
                    env={**os.environ, 'PYTHONPATH': scriptPath, 'PYTHONUNBUFFERED': '1'}
                )
                current_process = proc

                while True:
                    line = proc.stdout.readline()
                    if not line and proc.poll() is not None:
                        break
                    if line:
                        with buffer_lock:
                            output_buffer.append(line.strip())

                if proc.returncode != 0:
                    with buffer_lock:
                        output_buffer.append(f"Process exited with code {proc.returncode}")
                    break
            except Exception as e:
                with buffer_lock:
                    output_buffer.append(f"Error: {str(e)}")
                break
            finally:
                current_process = None

    Thread(target=run_commands).start()
    return jsonify({'status': 'started'})


@app.route('/console/output')
def get_output():
    with buffer_lock:
        return jsonify({'output': '\n'.join(output_buffer)})


# 分类路由保持不变
CATEGORY_MAPPING = {
    'A': 'A-Volume',
    'B': 'B-Short',
    'C': 'C-Doujin'
}


@app.route('/categories/<category_code>')
def category_view(category_code):
    data = load_data()
    category_name = CATEGORY_MAPPING.get(category_code)
    if not category_name or category_name not in data['data']:
        abort(404)

    entries = []
    for entry in data['data'][category_name]:
        entry_id = entry['id']
        entries.append({
            'prefix': entry['prefix'],
            'title': entry.get('title', 'undefined'),
            'relative_path': entry['relative_path'].replace('\\', '/'),
            'image_url': f"/static/images/{entry_id}.webp" if image_exists(entry_id) else None
        })

    page = request.args.get('page', 1, type=int)
    per_page = 100
    total = len(entries)
    return render_template('index.html',
                           entries=entries[(page - 1) * per_page: page * per_page],
                           page=page,
                           total_pages=(total + per_page - 1) // per_page,
                           category_code=category_code,
                           category_name=category_name)


@app.route('/search')
def search():
    keyword = request.args.get('q', '').strip().lower()
    if not keyword:
        return redirect(url_for('index'))

    data = load_data()
    results = []
    for category in data['data'].values():
        for entry in category:
            entry_id = entry.get('id', '').lower()
            entry_title = entry.get('title', '').lower()
            if keyword in entry_id or keyword in entry_title:
                results.append({
                    'prefix': entry['prefix'],
                    'title': entry.get('title', 'undefined'),
                    'relative_path': entry['relative_path'].replace('\\', '/'),
                    'image_url': f"/static/images/{entry['id']}.webp" if image_exists(entry['id']) else None
                })

    page = request.args.get('page', 1, type=int)
    per_page = 100
    total = len(results)
    start = (page - 1) * per_page
    end = start + per_page
    total_pages = (total + per_page - 1) // per_page

    return render_template('index.html',
                           entries=results[start:end],
                           page=page,
                           total_pages=total_pages,
                           search_query=keyword,
                           total_entries=total)


@app.route('/random')
def random_entries():
    data = load_data()
    all_entries = []
    for category in data['data'].values():
        all_entries.extend(category)
    import random
    random.seed()
    selected = random.sample(all_entries, 5) if len(all_entries) >= 5 else all_entries

    entries = []
    for entry in selected:
        entry_id = entry['id']
        entries.append({
            'prefix': entry['prefix'],
            'title': entry.get('title', 'undefined'),
            'relative_path': entry['relative_path'].replace('\\', '/'),
            'image_url': f"/static/images/{entry_id}.webp" if image_exists(entry_id) else None
        })

    return render_template('index.html',
                           entries=entries,
                           page=1,
                           total_pages=1,
                           is_random=True)


def check_port(
    port: int,
    host: str = "0.0.0.0",
    raise_exc: bool = False
) -> Tuple[bool, str]:
    """
    端口检测
    :param port: 端口号（必须为整数）
    :param host: 监听地址
    :param raise_exc: 是否抛出异常
    :return: (是否被占用, 描述信息)
    """
    try:
        port = int(port)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            s.close()
            return False, f"{host}:{port} is available"
    except ValueError:
        msg = f"Invalid port type: {type(port)}. Must be integer."
        if raise_exc:
            raise ValueError(msg)
        return True, msg
    except PermissionError:
        msg = f"{host}:{port} requires root privileges"
        if raise_exc:
            raise PermissionError(msg)
        return True, msg
    except OSError as e:
        if e.errno in (98, 10048):
            return True, f"{host}:{port} is already in use"
        msg = f"Unknown error: {str(e)}"
        if raise_exc:
            raise
        return True, msg


if __name__ == '__main__':
    print("working directory:", os.getcwd())
    print(check_port(port=app_port, host=app_host))  # 检测 HTTP 端口
    app.run(host=app_host, port=app_port, threaded=True)
