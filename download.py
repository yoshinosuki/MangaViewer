import subprocess
import os
import re
from concurrent.futures import ThreadPoolExecutor
import sys
import requests
from config import download_book_path

check_path = download_book_path


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


def check_continuous_sequence(numbers):
    """分析数字序列连续性"""
    if not numbers:
        return True, []

    expected = 1
    missing = []

    # 必须从1开始
    if numbers[0] != 1:
        missing.extend(range(1, numbers[0]))

    # 检测中间断档
    for num in numbers:
        if num > expected:
            missing.extend(range(expected, num))
            expected = num
        expected += 1

    return (len(missing) == 0), missing


def validate_image_files(directory):
    """校验目录中的图片文件命名合规性"""
    valid_numbers = []
    has_invalid = False
    img_exts = {'.jpg', '.png', '.webp'}

    for filename in os.listdir(directory):
        # 分割文件名与扩展名
        base, ext = os.path.splitext(filename)
        ext = ext.lower()

        if ext not in img_exts:
            continue  # 忽略非图片文件

        # 使用正则表达式校验纯数字文件名
        if re.fullmatch(r'^\d+$', base):
            valid_numbers.append(int(base))
        else:
            has_invalid = True

    return sorted(valid_numbers), has_invalid


def find_leaf_directories(root_dir):
    """深度优先搜索获取末级目录列表"""
    leaf_dirs = []
    for root, dirs, _ in os.walk(root_dir):
        if not dirs:  # 无子目录时判定为末级
            leaf_dirs.append(root)
    return leaf_dirs


def process_directory(target_dir):
    """处理单个目录的检测流程"""
    valid_numbers, has_invalid = validate_image_files(target_dir)

    # 打印非法文件名告警
    if has_invalid:
        print(f"[WARN] 非法文件名 {target_dir}")

    # 执行连续性检测
    if valid_numbers:
        is_continuous, missing = check_continuous_sequence(valid_numbers)
        if not is_continuous:
            print(f"[ERROR] 编号不连续 {target_dir}")
            print(f"缺失编号：{missing}")


def continuity_check():
    for leaf in find_leaf_directories(check_path):
        process_directory(leaf)


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
        continuity_check()
