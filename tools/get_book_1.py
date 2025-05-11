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
    except Exception as e:
        print(f"出现异常文件{file_path}:{e}")
        return False


def download(file_path, picture_url):
    """ 下载图片并检查完整性，支持重试，返回（是否成功，是否因404失败） """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36 QIHU 360SE",
    }
    max_retries = 5

    for attempt in range(max_retries):
        try:
            with requests.get(picture_url, headers=headers, stream=True, timeout=10) as r:
                if r.status_code == 404:
                    return False, True
                r.raise_for_status()

                # 流式写入文件
                with open(file_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                # 完整性校验
                if is_complete_image(file_path):
                    return True, False
                else:
                    os.remove(file_path)
                    continue

        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return False, True
            else:
                print(f'HTTP error {e.response.status_code}: {str(e)}')
        except (requests.RequestException, IOError) as e:
            print(f'尝试 {attempt + 1}/{max_retries} 失败: {str(e)}')
            time.sleep(random.uniform(5, 10))

    return False, False


def get_max_file_number(directory):
    """ 获取目录中最大的文件序号 """
    max_num = 0
    for filename in os.listdir(directory):
        num = int(re.sub(r'\D', '', filename))
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
        start_page = max(get_max_file_number(save_dir), 1)

        max_pages = 3000
        img_ext = ('jpg', 'png', 'webp')

        for i in range(start_page, max_pages + 1):
            downloaded = False
            all_ext_404 = True  # 初始假设所有扩展都是404

            for ext in img_ext:
                file_path = os.path.join(BookPath, webname, f'{i}.{ext}')
                image_url = f'{useurl}/{m}/{i}.{ext}'
                success, is_404 = download(file_path, image_url)

                if success:
                    downloaded = True
                    all_ext_404 = False  # 成功下载，重置标记
                    break
                else:
                    if not is_404:
                        all_ext_404 = False  # 存在非404错误

            if downloaded:
                continue  # 成功下载，继续下一页

            # 处理下载失败的情况
            if all_ext_404:
                if i == 1:
                    print(f'Invalid Book ID: {m}', flush=True)
                else:
                    print(f'Book Complete: {m} (Total Pages: {i - 1})', flush=True)
                break  # 所有扩展都返回404，结束本书下载
            else:
                print(f'Page {i} 下载失败，可能为临时错误，继续尝试后续页...', flush=True)


if __name__ == '__main__':
    main()
