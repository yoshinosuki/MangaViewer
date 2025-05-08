import datetime
import json
import os
import re
from typing import Dict, List, TypedDict, NotRequired

from config import root_dir, pdf_folders, json_path


# 类型定义 --------------------------------------------------
class Metadata(TypedDict):
    generated_at: str
    total_categories: int
    total_entries: int


class EnhancedEntry(TypedDict):
    relative_path: str
    id: str
    prefix: str
    category: str
    title: str
    tags: List[str]
    pdf_exists: NotRequired[bool]


class ProcessedData(TypedDict):
    metadata: Metadata
    data: Dict[str, List[EnhancedEntry]]


# 目录扫描模块 ----------------------------------------------
class DirectoryScanner:
    def __init__(self, root_path: str):
        self.root_path = os.path.normpath(root_path)
        self.exclude_pattern = re.compile(r'(wait|D-Serial)')

    def scan_valid_directories(self) -> Dict[str, List[EnhancedEntry]]:
        """返回结构：{分类: [条目字典]}"""
        categories = {}

        for root, dirs, _ in os.walk(self.root_path):
            relative_path = os.path.relpath(root, self.root_path)

            if self._should_skip(relative_path):
                continue

            if self._is_terminal_directory(root):
                entry = self._process_directory(relative_path)
                if entry:
                    categories.setdefault(entry['category'], []).append(entry)

        return categories

    def _should_skip(self, path: str) -> bool:
        """判断是否需要跳过目录"""
        return bool(self.exclude_pattern.search(path))

    def _is_terminal_directory(self, full_path: str) -> bool:
        """判断是否为最终节点目录（没有子目录）"""
        return not any(
            os.path.isdir(os.path.join(full_path, d))
            for d in os.listdir(full_path)
        )

    def _process_directory(self, rel_path: str) -> EnhancedEntry:
        """路径处理核心逻辑"""
        parts = rel_path.split(os.sep)
        if len(parts) < 2:
            print(f"无效路径跳过: {rel_path}")
            return None

        category = parts[0]
        sub_path = parts[1:]
        entry_id = sub_path[-1]

        prefix = f"{category[0]}{sub_path[0][0]}{entry_id}"

        return EnhancedEntry(
            category=category,
            id=entry_id,
            prefix=prefix,
            relative_path=rel_path,
            title="",  # 占位符，后续填充
            tags=[]  # 初始化为空列表
        )


# PDF检测模块 -----------------------------------------------
class PDFDetector:
    def __init__(self, pdf_paths: list):
        self.pdf_roots = [os.path.normpath(p) for p in pdf_paths]

    def batch_check(self, entries: Dict[str, List[EnhancedEntry]]) -> Dict[str, List[EnhancedEntry]]:
        """为所有条目添加PDF存在状态"""
        for category in entries:
            for entry in entries[category]:
                entry['pdf_exists'] = self._check_pdf_existence(entry['prefix'])
        return entries

    def _check_pdf_existence(self, prefix: str) -> bool:
        """多路径PDF检测逻辑"""
        target_file = f"{prefix}.pdf"

        for pdf_root in self.pdf_roots:
            candidate = os.path.join(pdf_root, target_file)
            if os.path.isfile(candidate):
                return True
            if os.name == 'nt' and self._windows_case_insensitive_check(pdf_root, target_file):
                return True
        return False

    def _windows_case_insensitive_check(self, root: str, filename: str) -> bool:
        """Windows环境下不区分大小写的文件检测"""
        target_lower = filename.lower()
        try:
            return any(f.lower() == target_lower for f in os.listdir(root))
        except FileNotFoundError:
            return False


# 标题映射模块 -----------------------------------------------
class TitleMapper:
    def __init__(self, db_path: str):
        self.title_db = self._load_title_db(db_path)

    def _load_title_db(self, path: str) -> Dict[str, dict]:
        """加载标题数据库（包含标签）"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)

            title_db = {}
            for item in raw_data:
                item_id = item.get('id')
                if item_id is None:
                    print(f"条目缺少id字段: {item}")
                    continue
                title = item.get('title', 'undefined')
                tags = item.get('tags', [])
                title_db[item_id] = {
                    'title': title,
                    'tags': tags
                }
            return title_db
        except FileNotFoundError:
            print(f"[警告] 标题数据库不存在: {path}")
            return {}
        except (KeyError, json.JSONDecodeError) as e:
            print(f"[错误] 标题数据库格式异常: {str(e)}")
            return {}

    def enrich_entries(self, data: ProcessedData) -> ProcessedData:
        """添加标题和标签信息"""
        valid_db = isinstance(self.title_db, dict)

        for category_entries in data['data'].values():
            for entry in category_entries:
                if valid_db:
                    db_entry = self.title_db.get(entry['id'], {})
                    entry['title'] = db_entry.get('title', 'undefined')
                    entry['tags'] = db_entry.get('tags', [])
                else:
                    entry['title'] = "数据库无效"
                    entry['tags'] = []
        return data


# 数据处理模块 -----------------------------------------------
class DataEnhancer:
    @staticmethod
    def add_timestamps(entries: Dict[str, List[EnhancedEntry]]) -> ProcessedData:
        """添加时间戳元数据"""
        timestamp = datetime.datetime.now().isoformat()
        return ProcessedData(
            metadata=Metadata(
                generated_at=timestamp,
                total_categories=len(entries),
                total_entries=sum(len(v) for v in entries.values())
            ),
            data=entries
        )

    @staticmethod
    def validate_structure(data: ProcessedData) -> bool:
        """数据完整性验证"""
        try:
            # 验证元数据
            assert isinstance(data['metadata']['generated_at'], str)
            assert isinstance(data['metadata']['total_categories'], int)
            assert isinstance(data['metadata']['total_entries'], int)

            # 验证条目数据
            for category, entries in data['data'].items():
                assert isinstance(category, str)
                for entry in entries:
                    required_keys = {'relative_path', 'id', 'prefix', 'category', 'title', 'tags'}
                    assert required_keys.issubset(entry.keys())
                    assert isinstance(entry['title'], str)
                    assert isinstance(entry['tags'], list)
                    for tag in entry['tags']:
                        assert isinstance(tag, str)

                    if 'pdf_exists' in entry:
                        assert isinstance(entry['pdf_exists'], bool)
            return True
        except (KeyError, AssertionError) as e:
            print(f"数据验证失败: {str(e)}")
            return False


# JSON序列化模块 --------------------------------------------
class JsonSerializer:
    def __init__(self, output_path: str):
        self.output_path = os.path.normpath(output_path)

    def save(self, data: ProcessedData) -> None:
        """安全保存JSON数据"""
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f,
                      indent=2,
                      ensure_ascii=False)

        self._validate_output(data)

    def _validate_output(self, original: ProcessedData) -> None:
        """输出后校验"""
        with open(self.output_path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)

        if loaded != original:
            raise ValueError("序列化数据不一致")


def tree_book():
    print(r"开始建立列表")
    config = {
        "root_folder": root_dir,
        "pdf_folders": pdf_folders,
        "title_db": r"./list/id_title.json",
        "output_json": json_path
    }

    # 初始化各模块
    scanner = DirectoryScanner(config["root_folder"])
    detector = PDFDetector(config["pdf_folders"])
    title_mapper = TitleMapper(config["title_db"])
    enhancer = DataEnhancer()
    serializer = JsonSerializer(config["output_json"])

    try:
        # 处理流程
        raw_data = scanner.scan_valid_directories()

        # 排序代码：按ID数值排序每个分类的条目
        for category in raw_data:
            raw_data[category].sort(key=lambda x: int(x['id']))

        pdf_checked = detector.batch_check(raw_data)
        stamped_data = enhancer.add_timestamps(pdf_checked)
        final_data = title_mapper.enrich_entries(stamped_data)

        if enhancer.validate_structure(final_data):
            serializer.save(final_data)
            print(f"成功生成带标题信息的JSON文件: {config['output_json']}")
            print(f"统计信息: {final_data['metadata']}")
        else:
            print("数据校验失败，终止保存")

    except Exception as e:
        print(f"处理过程中发生错误: {str(e)}")
        raise


# 主程序 ---------------------------------------------------
if __name__ == "__main__":
    tree_book()
