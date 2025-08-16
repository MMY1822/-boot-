import os
import shutil
import json
from pathlib import Path

# 配置参数
CONFIG = {
    'source_dirs': ['miui', 'hyper'],  # 要合并的源文件夹
    'target_dir': 'boot库',  # 合并目标文件夹
    'undo_log': 'merge_undo_log.json'  # 撤销日志文件
}


def merge_folders():
    """合并文件夹并记录操作日志"""
    # 获取当前脚本所在目录的上级目录
    base_dir = Path(__file__).parent.parent
    undo_data = []

    # 创建目标文件夹
    target_path = base_dir / CONFIG['target_dir']
    target_path.mkdir(parents=True, exist_ok=True)

    # 处理每个源文件夹
    for source_name in CONFIG['source_dirs']:
        source_path = base_dir / '爬取' / source_name

        if not source_path.exists():
            print(f"⚠️ 源文件夹不存在: {source_path}")
            continue

        # 遍历所有设备文件夹
        for device in os.listdir(source_path):
            device_path = source_path / device

            if not os.path.isdir(device_path):
                continue

            # 遍历设备下的所有分区文件夹
            for partition in os.listdir(device_path):
                partition_src = device_path / partition
                partition_dst = target_path / device / partition

                if not os.path.isdir(partition_src):
                    continue

                # 创建目标分区文件夹
                partition_dst.mkdir(parents=True, exist_ok=True)

                # 移动所有分区文件
                for file in os.listdir(partition_src):
                    src_file = partition_src / file
                    dst_file = partition_dst / file

                    if os.path.exists(dst_file):
                        print(f"⏩ 跳过已存在文件: {device}/{partition}/{file}")
                        continue

                    try:
                        shutil.move(str(src_file), str(dst_file))
                        undo_data.append({
                            'source': str(partition_src),
                            'device': device,
                            'partition': partition,
                            'file': file,
                            'src': str(src_file),
                            'dst': str(dst_file)
                        })
                        print(f"✅ 已移动 {source_name}/{device}/{partition}/{file}")
                    except Exception as e:
                        print(f"❌ 移动失败: {str(e)}")

    # 写入撤销日志
    if undo_data:
        with open(CONFIG['undo_log'], 'w') as f:
            json.dump(undo_data, f, indent=2)
        print(f"\n操作已记录到 {CONFIG['undo_log']}")
    else:
        print("\n没有文件需要移动")


def undo_merge():
    """撤销合并操作"""
    if not os.path.exists(CONFIG['undo_log']):
        print("没有可撤销的操作记录")
        return

    try:
        with open(CONFIG['undo_log'], 'r') as f:
            undo_data = json.load(f)
    except Exception as e:
        print(f"读取日志失败: {str(e)}")
        return

    restored_files = 0

    for record in reversed(undo_data):
        try:
            # 确保源目录存在
            os.makedirs(record['source'], exist_ok=True)

            # 移动文件回原位置
            shutil.move(record['dst'], record['src'])
            restored_files += 1
            print(f"↩️ 已还原 {record['device']}/{record['partition']}/{record['file']}")
        except Exception as e:
            print(f"❌ 还原失败: {record['file']} - {str(e)}")

    # 删除日志文件
    os.remove(CONFIG['undo_log'])
    print(f"\n已撤销 {restored_files}/{len(undo_data)} 个文件操作")


if __name__ == "__main__":
    import sys

    print("===start===")

    if '--undo' in sys.argv:
        print("\n正在撤销最近一次合并操作...")
        undo_merge()
        print("\n撤销操作完成！")
    else:
        print("\n开始合并分区文件...")
        merge_folders()
        print("\n合并操作完成！使用 --undo 参数可撤销操作")