import os
import json
from PIL import Image, ImageFile
import gc
import datetime
import shutil
from config import json_path, downloadPdfPath, download_book_path

ImageFile.LOAD_TRUNCATED_IMAGES = True

# 配置
base_folder_paths = [download_book_path]
temp_folder = r'..\book\temp'
quality = 20


def read_json_config(json_path):
    """读取JSON配置并生成PDF生成策略"""
    config = {}
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

            # 遍历所有分类条目
            for category, items in data['data'].items():
                for item in items:
                    # 路径处理
                    path_segments = item['relative_path'].split('\\')
                    folder_name = path_segments[-1]  # 获取最底层文件夹名

                    # 生成配置策略
                    config[folder_name] = {
                        'need_generate': not item['pdf_exists'],  # 核心逻辑：pdf_exists为False时需要生成
                        'pdf_name': item['prefix']  # prefix + id:AA3285812
                    }
        return config

    except Exception as e:
        print(f"配置加载失败: {str(e)}")
        return {}


pdf_config = read_json_config(json_path)


def should_generate_pdf(folder_name):
    """判断是否需要生成PDF"""
    return pdf_config.get(folder_name, {}).get('need_generate', False)


def get_pdf_name(folder_name):
    """获取PDF文件名"""
    return pdf_config.get(folder_name, {}).get('pdf_name', folder_name)


def safe_image_generator(img_folder, img_files, error_log):
    """安全图像加载器"""
    for f in img_files[1:]:  # 跳过首张图片
        img_path = os.path.join(img_folder, f)
        try:
            # 打开图片并保持引用
            img = Image.open(img_path)
            if img.mode == 'P':
                img = img.convert('RGB')
            # 创建内存副本
            img_copy = img.copy()
            yield img_copy
        except Exception as e:
            error_log.append(f"处理失败 {img_path}: {str(e)}")
        finally:
            # 显式关闭原图
            if 'img' in locals():
                img.close()


def process_images(input_folder, output_folder):
    """带严格验证的图像处理"""
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    processed_count = 0
    for filename in os.listdir(input_folder):
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, filename)

        # 验证文件有效性
        if not os.path.isfile(input_path):
            print(f"忽略非文件项: {input_path}")
            continue

        try:
            with Image.open(input_path) as img:
                # 验证图像模式
                if img.mode not in ['RGB', 'RGBA', 'L', 'LA']:
                    print(f"非常规模式跳过: {input_path} ({img.mode})")
                    continue

                # 转换透明通道
                if img.mode in ['RGBA', 'LA']:
                    img = img.convert('RGB')

                # 验证图像尺寸
                if img.size[0] * img.size[1] > 10000 * 10000:
                    print(f"超大图像跳过: {input_path} ({img.size})")
                    continue

                img.save(output_path, quality=quality, optimize=True)
                processed_count += 1

        except Exception as e:
            print(f"图像处理失败: {input_path} - {str(e)}")
            continue

    return processed_count


def generate_pdf(folder_path, error_log):
    folder_name = os.path.basename(folder_path)

    if not should_generate_pdf(folder_name):
        # print(f"跳过已存在PDF的文件夹: {folder_name}")
        return

    temp_path = os.path.join(temp_folder, folder_name)

    # 清理临时目录
    if os.path.exists(temp_path):
        shutil.rmtree(temp_path)
    os.makedirs(temp_path)

    try:
        # 处理图片到临时目录
        processed_count = process_images(folder_path, temp_path)
        if processed_count == 0:
            error_log.append(f"{folder_path} - 无有效图片")
            return

        # 获取排序后的图片列表
        img_files = sorted(
            [f for f in os.listdir(temp_path) if f.lower().endswith(('.jpg', '.png', '.webp'))],
            key=lambda x: int(''.join(filter(lambda c: c.isdigit(), x)) or 0)
        )

        # 生成PDF路径
        pdf_path = os.path.join(downloadPdfPath, f"{get_pdf_name(folder_name)}.pdf")

        # 处理首张图片
        first_img_path = os.path.join(temp_path, img_files[0])
        try:
            with Image.open(first_img_path) as first_img:
                if first_img.mode == 'P':
                    first_img = first_img.convert('RGB')

                # 创建首图副本
                first_img_copy = first_img.copy()

                # 生成PDF
                first_img_copy.save(
                    pdf_path,
                    save_all=True,
                    append_images=safe_image_generator(temp_path, img_files, error_log),
                    quality=quality,
                    optimize=True
                )
                print(f"PDF生成成功: {pdf_path}")

        finally:
            # 显式关闭副本
            if 'first_img_copy' in locals():
                first_img_copy.close()

    except Exception as e:
        error_log.append(f"{folder_path} - {str(e)}")
        print(f"PDF生成失败: {folder_path}")

    finally:
        # 确保清理资源
        if os.path.exists(temp_path):
            shutil.rmtree(temp_path)
        gc.collect()


def batch_convert(base_paths):
    """批量转换入口"""
    error_log = []
    start_time = datetime.datetime.now()

    for base in base_paths:
        if not os.path.exists(base):
            continue

        for root, dirs, _ in os.walk(base):
            for dir_name in dirs:
                folder_path = os.path.join(root, dir_name)
                generate_pdf(folder_path, error_log)

    # 保存错误日志
    if error_log:
        log_file = f"pdf_errors_{start_time.strftime('%Y%m%d_%H%M%S')}.txt"
        with open(log_file, 'w') as f:
            f.write('\n'.join(error_log))
        print(f"错误日志已保存至: {log_file}")

    print(f"任务完成，总耗时: {datetime.datetime.now() - start_time}")


if __name__ == "__main__":
    print("请确保manga已经分类完毕")
    print(f"请确保manga的状态已更新：{json_path}")
    # 清理临时目录
    if os.path.exists(temp_folder):
        shutil.rmtree(temp_folder)

    # 执行转换
    batch_convert(base_folder_paths)
