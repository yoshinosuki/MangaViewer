import subprocess
import os
from concurrent.futures import ThreadPoolExecutor
import sys
import requests
from config import download_book_path


def test_web():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36 QIHU 360SE",
    }
    max_retries = 4  # 最大重试次数
    for i in range(max_retries):
        try:
            r = requests.get('https://nhentai.net', headers=headers, stream=True)
            if r.status_code == 200:
                print(f"网络测试成功")
                return True
        except requests.exceptions.RequestException as e:
            print(f'Retry {i + 1}/{max_retries} after {e}')
            pass


def run_script(script):
    with subprocess.Popen(
            [sys.executable, "-u", script],  # -u参数禁用缓冲
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,  # 行缓冲模式
            text=True,
            encoding='utf-8'
    ) as process:

        with open('log.txt', 'a', encoding='utf-8') as log_file:
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    # 同时输出到控制台和日志文件
                    print(line.strip())  # 实时显示
                    log_file.write(line)  # 写入日志

        return process.returncode


def main():
    print("开始下载进程")
    os.makedirs(download_book_path, exist_ok=True)

    scripts = ["./tools/get_book_1.py", "./tools/get_book_2.py", "./tools/get_book_3.py"]

    with ThreadPoolExecutor() as executor:
        executor.map(run_script, scripts)

    print("下载完成，下载记录已保存")


def create_flag(filename='flag'):
    """生成flag文件"""
    with open(filename, 'w') as f:
        pass


if __name__ == '__main__':
    print("当前工作目录:", os.getcwd())
    if test_web():
        main()
        create_flag()
