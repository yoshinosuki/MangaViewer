import datetime
import os
import json
import glob
from PIL import Image
from tree_book import tree_book
from classify import move_folders
from config import root_dir, json_path

# 配置
id_json_path = "log.txt"
dest_dir = r'.\static\images'
quality = 20


def check_flag(filename='flag'):
    """检测并删除flag文件"""
    if os.path.exists(filename):
        os.remove(filename)
        return True
    return False


def convert_to_jpg(source_path, dest_path):
    """将任意图片格式转换为JPG格式"""
    try:
        img = Image.open(source_path)
        # 转换颜色模式（处理带透明层的PNG）
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        img.save(dest_path, 'JPEG', quality=quality)
        return True
    except Exception as e:
        print(f"格式转换失败：{source_path} -> {dest_path} | 错误：{str(e)}")
        return False


def main():

    # 创建目标文件夹
    os.makedirs(dest_dir, exist_ok=True)

    # 读取JSON数据
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 支持的图片扩展名
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.webp']

    # 处理所有条目
    for category in data['data'].values():
        for entry in category:
            relative_path = entry['relative_path']
            id = entry['id']

            # 构建完整源路径
            path_parts = relative_path.split('\\')
            full_path = os.path.join(root_dir, *path_parts)

            # 验证路径是否存在
            if not os.path.exists(full_path):
                print(f"路径不存在：{full_path}")
                continue

            # 查找所有图片文件
            image_files = []
            for ext in image_extensions:
                image_files.extend(glob.glob(os.path.join(full_path, ext)))

            if not image_files:
                print(f"未找到图片文件：{full_path}")
                continue

            # 按文件名排序并获取第一个
            first_image = sorted(image_files)[0]

            # 构建目标路径（扩展名）
            dest_path = os.path.join(dest_dir, f"{id}.webp")

            # 存在性检查
            if os.path.exists(dest_path):
                # print(f"文件已存在，跳过：{dest_path}")
                continue

            # 执行格式转换
            if convert_to_jpg(first_image, dest_path):
                print(f"转换成功：{os.path.basename(first_image)} -> {id}.webp")
            else:
                # 删除可能生成的损坏文件
                if os.path.exists(dest_path):
                    os.remove(dest_path)


if __name__ == '__main__':
    # tree_book()
    # main()

    data_path = os.getenv("DATA_PATH", id_json_path)
    if check_flag():
        print("检测到需要更新数据，开始收集")
        move_folders()
        tree_book()
        main()
        print('数据更新完毕')
