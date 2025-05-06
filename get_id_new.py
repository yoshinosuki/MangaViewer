import argparse
import os
import random
import re
import shutil
import time
import requests
from bs4 import BeautifulSoup
import json
from playwright.sync_api import sync_playwright

all_page_num = 6  # 控制需要获取数据的数字页码


def parse_html(html_text):
    """
    增强型HTML解析器，从图片URL提取精确画廊ID
    返回结构：[{"id": "3234276", "title": "sample", "tags": ["3391","8693",...]}, ...]
    """
    soup = BeautifulSoup(html_text, 'html.parser')
    galleries = soup.find_all('div', class_='gallery')

    result = []
    id_pattern = re.compile(r'galleries/(\d+)/')

    for gallery in galleries:
        try:
            # 提取标签列表
            raw_tags = gallery.get('data-tags', '')
            tags = raw_tags.split() if raw_tags else []

            # 定位图片标签
            img_tag = gallery.find('img', class_='lazyload') or \
                      gallery.find('noscript').find('img')

            # 从data-src或src提取URL
            img_url = img_tag.get('data-src') or img_tag.get('src')

            # 精确匹配画廊ID
            match = id_pattern.search(img_url)
            gallery_id = match.group(1) if match else "unknown"

            # 提取标题
            caption_div = gallery.find('div', class_='caption')
            title = caption_div.text.strip() if caption_div else "No Title"

            result.append({
                "id": gallery_id,
                "title": title,
                "tags": tags  # tag
            })

        except Exception as e:
            print(f"解析异常：{str(e)}")
            continue

    return result


def get_html(page, url, max_retries=3):
    """
    增强型页面获取函数
    新增功能：
    1. 自动重试机制
    2. 随机延迟防止封禁
    3. 网络状态监控
    """
    for attempt in range(max_retries):
        try:
            page.goto(url, timeout=60000)
            if page.locator('div.gallery').count() > 0:
                return page.content()
            else:
                print(f"第{attempt + 1}次重试：页面元素未加载成功")
                time.sleep(random.uniform(2, 5))
        except Exception as e:
            print(f"请求异常：{str(e)}")
            time.sleep(attempt * 5)  # 指数退避

    raise Exception(f"请求失败：{url}")


def save_data(data, base_path='./list'):
    os.makedirs(base_path, exist_ok=True)
    json_path = os.path.join(base_path, 'id_title.json')
    txt_path = os.path.join(base_path, 'id_new.txt')
    temp_path = None  # 显式初始化

    try:
        # 写入TXT文件
        with open(txt_path, 'w', encoding='utf-8', errors='replace') as f_txt:
            for item in data:
                f_txt.write(f"{item['id']}\n")

        # 处理JSON文件
        existing_data = load_json_safely(json_path)
        existing_ids = {item['id'] for item in existing_data}
        new_data = [item for item in data if item['id'] not in existing_ids]

        # 原子化写入准备
        temp_path = f"{json_path}.tmp"  # 正式赋值
        with open(temp_path, 'w', encoding='utf-8') as f_json:
            json.dump(
                existing_data + new_data,
                f_json,
                indent=2,
                ensure_ascii=False,
                separators=(',', ': ')
            )

        # 验证流程
        validate_json(temp_path)
        os.replace(temp_path, json_path)

    except Exception as e:
        # 安全清理临时文件
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError as cleanup_error:
                print(f"临时文件清理失败：{cleanup_error}")

        # 回滚TXT写入（如果需要）
        if isinstance(e, (IOError, json.JSONDecodeError)):
            try:
                with open(txt_path, 'r+', encoding='utf-8') as f_txt:
                    lines = f_txt.readlines()
                    f_txt.seek(0)
                    f_txt.writelines(lines[:-len(data)])
                    f_txt.truncate()
            except Exception as rollback_error:
                print(f"TXT回滚失败：{rollback_error}")

        raise


def validate_json(file_path):
    """JSON文件完整性验证"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("JSON结构验证失败")
        for item in data:
            if 'id' not in item or 'title' not in item:
                raise ValueError("数据字段缺失")


def main(url_prefix):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        all_data = []

        for page_num in range(1, all_page_num):
            url = f"{url_prefix}{page_num}"
            print(f"正在处理第{page_num}页")
            try:
                html = get_html(page, url)
                page_data = parse_html(html)
                save_data(page_data)
                all_data.extend(page_data)

                # 动态延迟（根据页面数据量调整）
                delay = max(1, round(5 - len(page_data) / 10))
                time.sleep(delay)

            except Exception as e:
                print(f"页面{page_num}处理失败：{str(e)}")
                continue

        browser.close()

        # 最终数据校验
        print(f"总计采集：{len(all_data)}条数据")
        # print(f"去重后唯一ID数量：{len({x['id'] for x in all_data})}")


def load_json_safely(json_path):
    """安全加载JSON数据"""
    if not os.path.exists(json_path):
        return []

    file_size = os.path.getsize(json_path)
    if file_size == 0:
        return []

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

            # 数据格式校验
            if not isinstance(data, list):
                print("数据格式异常，重置存储文件")
                return []

            return data

    except (json.JSONDecodeError, ValueError) as e:
        print(f"JSON解析失败：{str(e)}")
        print("尝试恢复最后有效数据...")
        return recover_corrupted_json(json_path)

    except Exception as e:
        print(f"未知错误：{str(e)}")
        return []


def recover_corrupted_json(json_path):
    """尝试恢复损坏的JSON文件"""
    backup_path = f"{json_path}.bak"
    try:
        # 创建备份
        shutil.copyfile(json_path, backup_path)

        # 尝试逐行恢复
        with open(json_path, 'r', encoding='utf-8') as f:
            content = f.read()
            last_valid_pos = content.rfind(']')  # 查找最后有效结束符

            if last_valid_pos != -1:
                repaired = content[:last_valid_pos + 1]
                return json.loads(repaired)

        # 恢复失败则返回空
        return []

    except Exception as e:
        print(f"恢复失败：{str(e)}")
        return []


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


if __name__ == '__main__':
    if test_web():
        parser = argparse.ArgumentParser(description='URLs.')
        parser.add_argument('url', type=str, nargs='?',
                            default='https://nhentai.net/search/?q=uncensored&page=',
                            help='The URL prefix to use')
        # 无码uncensored 中文%5Bchinese%5D 大于60页pages%3A%3E60
        # 无码中文：https://nhentai.net/search/?q=uncensored+%5Bchinese%5D&page=
        # 无码中文单行本：https://nhentai.net/search/?q=pages%3A%3E60+uncensored+%5Bchinese%5D&page=
        # 中文单行本：https://nhentai.net/search/?q=pages%3A%3E100+%5Bchinese%5D&page=
        args = parser.parse_args()
        main(args.url)
