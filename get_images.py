import datetime
import os
import json
import glob
from PIL import Image

from config import root_dir, json_path

# 配置
id_json_path = "log.txt"
dest_dir = r'.\static\images'
quality = 20


def check_data_status(path, mode="recent", ref_time=None, time_window=None):
    """
    检测文件/文件夹是否为最新版本

    参数:
    path (str): 文件或文件夹路径
    mode (str): 检测模式 ["recent"检查近期更新 | "reference"对比参考时间]
    ref_time (datetime/float): 参考时间（mode=reference时必需）
    time_window (timedelta): 时间窗口（mode=recent时必需）

    返回:
    str: True 或 False
    """

    def check_file(file_path):
        """单个文件的检测逻辑"""
        try:
            mod_time = os.path.getmtime(file_path)
            if mode == "recent":
                return (datetime.datetime.now().timestamp() - mod_time) <= time_window.total_seconds()
            return mod_time >= (ref_time.timestamp() if isinstance(ref_time, datetime.datetime) else ref_time)
        except Exception:
            return False

    # 参数验证
    if not os.path.exists(path):
        return False
    if mode not in ["recent", "reference"]:
        raise ValueError("检测模式错误，支持 'recent' 或 'reference'")
    if mode == "recent" and not time_window:
        raise ValueError("近期检测模式需要 time_window 参数")
    if mode == "reference" and not ref_time:
        raise ValueError("参考时间检测模式需要 ref_time 参数")

    # 文件检测
    if os.path.isfile(path):
        return True if check_file(path) else False

    # 文件夹检测
    has_qualified = False  # 近期模式使用
    all_qualified = True  # 参考时间模式使用

    for root, _, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            status = check_file(file_path)

            if mode == "recent":
                if status:
                    has_qualified = True
                    break  # 发现符合条件的立即终止
            else:
                if not status:
                    all_qualified = False
                    break  # 发现不符合条件的立即终止

        # 根据检测模式提前终止遍历
        if (mode == "recent" and has_qualified) or (mode == "reference" and not all_qualified):
            break

    if mode == "recent":
        return True if has_qualified else False
    return True if all_qualified else False


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
    # main()

    data_path = os.getenv("DATA_PATH", id_json_path)
    if check_data_status(
        data_path,
        mode="recent",
        time_window=datetime.timedelta(minutes=5)
    ):
        print("检测到需要更新数据，开始收集")
        main()
        print('数据更新完毕')
