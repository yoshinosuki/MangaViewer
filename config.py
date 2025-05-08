import json
import os

# 加载JSON配置文件
_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
_CONFIG_PATH = os.path.join(_CONFIG_DIR, 'config.json')

try:
    with open(_CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # 解析路径配置（处理斜杠问题）
    root_dir = os.path.normpath(config["root_dir"])
    download_book_path = os.path.join(root_dir, 'wait')
    json_path = os.path.normpath(config["json_path"])
    downloadPdfPath = os.path.normpath(config["downloadPdfPath"])
    pdf_folders = [os.path.normpath(p) for p in config["pdf_folders"]]
    scriptPath = os.path.normpath(config["script_path"])
    pythonExe = os.path.normpath(config["python_executable"])
    app_host = os.path.normpath(config["app_host"])
    app_port = os.path.normpath(config["app_port"])

    raw_script_path = config["script_path"]
    scriptPath = os.path.normpath(
        raw_script_path if raw_script_path.strip() != ""
        else os.path.dirname(os.path.abspath(__file__))
    )


except FileNotFoundError:
    raise Exception(f"配置文件 {_CONFIG_PATH} 未找到")
except KeyError as e:
    raise Exception(f"配置文件中缺少必要的键：{e}")
except json.JSONDecodeError:
    raise Exception("配置文件格式错误，请检查JSON语法")
