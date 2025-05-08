import os
import re
import requests
import time
import random
from PIL import Image

from config import download_book_path

downloadPath = r'.\list\target_1.txt'
BookPath = download_book_path
useurl = f'https://i3.nhentai.net/galleries'


def is_complete_image(file_path):
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    except Exception:
        print(f"出现异常文件{file_path}")
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
                    return False
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
    with open(downloadPath, 'r') as f:
        lines = [l.strip() for l in f if l.strip()]

    for m in map(int, lines):
        webname = str(m)
        save_dir = os.path.join(BookPath, webname)
        os.makedirs(save_dir, exist_ok=True)
        start_page = max(get_max_file_number(save_dir), 1)  # 获取起始页数
        """单点续传"""

        max_pages = 3000
        img_ext = ('jpg', 'png', 'webp')

        for i in range(start_page, max_pages + 1):
            downloaded = False
            for ext in img_ext:
                file_path = os.path.join(BookPath, webname, f'{i}.{ext}')
                image_url = f'{useurl}/{m}/{i}.{ext}'
                if download(file_path, image_url):
                    downloaded = True
                    break

            if not downloaded:
                if i == 1:
                    print(f'Invalid Book ID: {m}', flush=True)
                else:
                    print(f'Book Complete: {m} (Total Pages: {i - 1})', flush=True)
                break


if __name__ == '__main__':
    main()
