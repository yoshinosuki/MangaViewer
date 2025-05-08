import os
import random
import shutil
from PIL import Image
from config import download_book_path, root_dir

# 全局路径
root_folder = download_book_path
root_output_folder = root_dir
color_output = "./list/color_useid.txt"
quantity_output = "./list/quantity_useid.txt"

long_color_dir = os.path.normpath(os.path.join(root_output_folder, "A-Volume", "B-color"))
long_monochrome_dir = os.path.normpath(os.path.join(root_output_folder, "A-Volume", "A-Monochrome"))
short_color_dir = os.path.normpath(os.path.join(root_output_folder, "B-Short", "B-color"))
short_monochrome_dir = os.path.normpath(os.path.join(root_output_folder, "B-Short", "A-Monochrome"))


def is_color_image(image_path):
    """彩色像素检测"""
    try:
        with Image.open(image_path) as img:
            if img.mode not in ('RGB', 'RGBA'):
                return 0.0

            img = img.convert('RGB')
            pixels = list(img.getdata())
            total = len(pixels)
            if total == 0:
                return 0.0

            # 使用生成器表达式优化内存
            color_pixels = sum(1 for (r, g, b) in pixels if abs(r - g) > 25 or abs(g - b) > 25)
            return (color_pixels / total) * 100
    except Exception as e:
        print(f"Image processing error: {image_path} - {str(e)}")
        return 0.0


def analyze_quantity_folders(root_folder, output_path):
    """数量分析"""
    quantity_map = {}

    # 自底向上遍历统计
    for root, dirs, files in os.walk(root_folder, topdown=False):
        img_count = sum(1 for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp')))
        # 累加子目录数量
        img_count += sum(quantity_map[os.path.join(root, d)] for d in dirs)
        quantity_map[root] = img_count

    # 筛选结果并写入文件
    result = [k for k, v in quantity_map.items() if v > 60 and k != root_folder]
    with open(output_path, 'w') as f:
        f.write('\n'.join(result))

    return set(result)


def analyze_color_folders(root_folder, output_path):
    """颜色分析"""
    color_folders = []

    for folder, _, files in os.walk(root_folder):
        if folder == root_folder:
            continue

        img_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp'))]
        if not img_files:
            continue

        # 动态采样数量：5-20张（根据文件夹大小）
        sample_size = min(max(len(img_files) // 10, 5), 20)
        samples = random.sample(img_files, min(sample_size, len(img_files)))

        # 并行处理图片分析
        color_scores = [is_color_image(os.path.join(folder, f)) for f in samples]
        avg_score = sum(color_scores) / len(color_scores)

        if avg_score < 25:  # 调整阈值到25%
            color_folders.append(folder)

    with open(output_path, 'w') as f:
        f.write('\n'.join(color_folders))

    return set(color_folders)


def move_folders():
    """带冲突检测的移动逻辑"""
    # 仅处理直接子目录
    all_subdirs = {os.path.normpath(os.path.join(root_folder, d))
                   for d in os.listdir(root_folder)
                   if os.path.isdir(os.path.join(root_folder, d))}

    # 获取分析结果
    quantity = analyze_quantity_folders(root_folder, quantity_output)
    color = analyze_color_folders(root_folder, color_output)

    # 分类映射表
    category_conditions = {
        'long_color': (long_color_dir, lambda x: x in quantity and x not in color),
        'long_mono': (long_monochrome_dir, lambda x: x in quantity and x in color),
        'short_color': (short_color_dir, lambda x: x not in quantity and x not in color),
        'short_mono': (short_monochrome_dir, lambda x: x not in quantity and x in color)
    }

    # 创建目标目录
    for target_dir in {v[0] for v in category_conditions.values()}:
        os.makedirs(target_dir, exist_ok=True)

    # 执行移动操作
    moved = set()
    conflicts = []

    for category, (target_dir, condition) in category_conditions.items():
        for folder in filter(condition, all_subdirs):
            if folder in moved:
                continue

            dest = os.path.normpath(os.path.join(target_dir, os.path.basename(folder)))

            if os.path.exists(dest):
                conflicts.append(f"CONFLICT: {folder} -> {dest}")
                continue

            try:
                shutil.move(folder, dest)
                moved.add(folder)
                print(f"MOVED [{category}]: {os.path.basename(folder)} -> {dest}")
            except Exception as e:
                print(f"ERROR: {folder} | {str(e)}")

    # 输出冲突报告
    if conflicts:
        print("\n=== Conflicts Report ===")
        print('\n'.join(conflicts))


if __name__ == "__main__":
    move_folders()
