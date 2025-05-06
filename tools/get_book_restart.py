# 该程序留给想要只根据id下载不记录其他东西时所使用
import os
import re
import requests
import time
import random
from PIL import Image

from config import download_book_path

downloadPath = r'..\list\target_restart.txt'
BookPath = download_book_path
useurl = f'https://i3.nhentai.net/galleries/'

# 获取脚本所在的目录
script_dir = os.path.dirname(os.path.abspath(__file__))

# 设置工作目录为脚本所在的目录
os.chdir(script_dir)


def is_complete_image(file_path):
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    except Exception:
        return False


def download(file_path, picture_url):
    """ 下载图片并检查完整性，支持重试 """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36 QIHU 360SE",
    }
    max_retries = 4

    for attempt in range(max_retries):
        try:
            with requests.get(picture_url, headers=headers, stream=True, timeout=10) as r:
                if r.status_code == 404:
                    return True
                r.raise_for_status()  # 自动处理4xx/5xx错误

                # 流式写入文件
                with open(file_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:  # 过滤keep-alive空块
                            f.write(chunk)

                # 完整性校验
                if is_complete_image(file_path):
                    return True
                else:
                    print(f'文件不完整: {file_path}')
                    os.remove(file_path)
                    continue

        except (requests.RequestException, IOError) as e:
            print(f'尝试 {attempt+1}/{max_retries} 失败: {str(e)}')
            time.sleep(random.uniform(1, 3))

    return False


def get_max_file_number(directory):
    """ 获取目录中最大的文件序号 """
    max_num = 0
    for filename in os.listdir(directory):
        num = int(re.sub(r'\D', '', filename))  # 提取数字
        if num > max_num:
            max_num = num
    return max_num


def main():
    global webname
    with open(downloadPath, 'r') as f:
        lines = f.readlines()
    for line in lines:
        m = int(line.strip())
        prefix_url = f'{useurl}{m}/'
        match = re.search(r'galleries/(\d+)', prefix_url)
        if match:
            webname = str(m)
        os.makedirs(os.path.join(BookPath, webname), exist_ok=True)
        n = 3000  # 页数
        start_page = get_max_file_number(os.path.join(BookPath, webname))  # 获取起始页数
        start_page = start_page if start_page > 0 else 1
        """单点续传"""
        for i in range(start_page, n + 1):  # 从最大序号开始
            file_path = os.path.join(BookPath, webname, f'{i}.jpg')
            picture_url = f'{prefix_url}{i}.jpg'
            if not download(file_path, picture_url):
                file_path = os.path.join(BookPath, webname, f'{i}.png')
                picture_url = f'{prefix_url}{i}.png'
                if not download(file_path, picture_url):
                    file_path = os.path.join(BookPath, webname, f'{i}.webp')
                    picture_url = f'{prefix_url}{i}.webp'
                    if not download(file_path, picture_url):
                        if i == 1:  # 第一页就失败说明图册不存在
                            print(f'Invalid Book ID: {m}', flush=True)
                        else:       # 中途失败说明正常结束
                            print(f'Book Complete: {m} (Total Pages: {i-1})', flush=True)
                        break


if __name__ == '__main__':
    main()
