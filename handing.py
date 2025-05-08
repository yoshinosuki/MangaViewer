import os
from datetime import datetime

# 获取脚本所在的目录
script_dir = os.path.dirname(os.path.abspath(__file__))

# 设置工作目录为脚本所在的目录
os.chdir(script_dir)

# 定义文件路径
id_file_path = './list/id.txt'
new_file_path = './list/id_new.txt'
output_file_path = './list/id_filtered.txt'


def read_file(file_path):
    """ 读取文件并返回每行内容组成的集合 """
    if not os.path.exists(file_path):
        with open(file_path, 'w') as file:
            pass
    with open(file_path, 'r') as file:
        return set(line.strip() for line in file if line.strip())


def write_file(file_path, data):
    """ 将数据写入文件 """
    with open(file_path, 'w') as file:
        for item in data:
            file.write(f"{item}\n")


def append_to_file(file_path, data):
    """ 将数据追加到文件 """
    with open(file_path, 'a') as file:
        for item in data:
            file.write(f"{item}\n")


def remove_duplicates(id_file, new_file, output_file):
    """ 移除new_file中在id_file中出现过的数字 """
    id_set = read_file(id_file)
    new_set = read_file(new_file)
    # 从new_set中移除在id_set中存在的项
    result_set = new_set - id_set
    write_file(output_file, result_set)


def read_numbers_from_file(filename):
    with open(filename, 'r') as file:
        numbers = file.read().splitlines()
        return [int(num) for num in numbers]


def write_numbers_to_file(filename, numbers):
    with open(filename, 'w') as file:
        for num in numbers:
            file.write(f"{num}\n")


def distribute_numbers(numbers):
    """ 分配id """
    files = {1: [], 2: [], 3: []}
    length = len(numbers)
    print(f"去重后ID数量：{length}")
    # 按照顺序分配数字
    for i in range(length):
        files[(i % 3) + 1].append(numbers[i])
    remainder = length % 3
    extra_numbers = []
    if remainder == 1:
        extra_numbers.append(numbers[-1])
    elif remainder == 2:
        extra_numbers.append(numbers[-2])
        extra_numbers.append(numbers[-1])
    for num in extra_numbers:
        if num in files[1]:
            files[1].remove(num)
    files[1].extend(extra_numbers)
    return files


def log_append_action(log_file, data):
    """ 记录追加操作到日志文件 """
    with open(log_file, 'a') as file:
        file.write(f"Appended on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:\n")
        for item in data:
            file.write(f"{item}\n")
            # print(f"{item}\n")
        file.write("\n")


def log_append_action_notime(log_file, data):
    """ 记录追加操作到日志文件 """
    with open(log_file, 'a') as file:
        for item in data:
            file.write(f"{item}\n")
            # print(f"{item}\n")
        file.write("\n")


def main():
    # 执行去重操作
    remove_duplicates(id_file_path, new_file_path, output_file_path)
    numbers = read_numbers_from_file(output_file_path)
    distributed_files = distribute_numbers(numbers)
    for i in range(1, 4):
        write_numbers_to_file(f'./list/target_{i}.txt', distributed_files[i])

    # 追加new_filtered.txt内容到id.txt并记录日志
    new_filtered_set = read_file(output_file_path)
    append_to_file(id_file_path, new_filtered_set)
    log_append_action('./list/log.txt', new_filtered_set)


if __name__ == "__main__":
    main()
    print("分配任务完成")
