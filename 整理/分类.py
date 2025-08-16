import os
import shutil
import re
import json
from pathlib import Path

# 更新后的配置参数（按照截图中的分类体系）
CONFIG = {
    'source_dir': 'boot库',  # 源文件夹
    'target_dir': 'boot库_整理',  # 整理后的目标文件夹
    'undo_log': 'organize_undo_log.json',  # 撤销日志文件
    'series_categories': {
        'Redmi': {
            '数字系列': r'\b(\d+[A-Za-z]*)\b',
            'K系列': r'\bK\d+[A-Za-z]*\b',
            'A系列': r'\bA\d+[A-Za-z]*\b',
            'Note系列': r'\bNote\d+[A-Za-z]*\b',
            'Turbo系列': r'\bTurbo\d+[A-Za-z]*\b',
            'S系列': r'\bS\d+[A-Za-z]*\b',
            'Pad系列': r'\b(平板|Pad)\b',
            '其他': r'.*'
        },
        # 更新小米系列分类（按照截图）
        '小米': {
            'Pad系列': r'\b(平板|Pad)\b',
            'Mix系列': r'\bMIX\b',
            'Max系列': r'\bMax\b',
            'Civi系列': r'\bCivi\b',
            'Play系列': r'\bPlay\b',
            'Note系列': r'\bNote\b',
            'CC系列': r'\bCC\b',
            '数字系列': r'\b(\d+[A-Za-z]*)\b',
            '其他': r'.*'
        }
    }
}


def get_device_series(device_name):
    """根据设备名称确定其所属系列"""
    # 确定品牌大类
    brand = "Redmi" if re.search(r'^(Redmi|REDMI|红米)', device_name, re.IGNORECASE) else "小米"

    # 检查是否平板设备
    if re.search(CONFIG['series_categories'][brand]['Pad系列'], device_name, re.IGNORECASE):
        return brand, "Pad系列"

    # 检查其他系列（按照配置顺序）
    for series, pattern in CONFIG['series_categories'][brand].items():
        if series in ["其他", "Pad系列"]:
            continue
        if re.search(pattern, device_name, re.IGNORECASE):
            return brand, series

    # 默认归类为"其他"
    return brand, "其他"


def organize_devices():
    """整理设备文件夹"""
    base_dir = Path(__file__).parent.parent
    source_path = base_dir / CONFIG['source_dir']
    target_path = base_dir / CONFIG['target_dir']
    undo_data = []

    # 创建目标文件夹
    target_path.mkdir(parents=True, exist_ok=True)

    # 遍历所有设备文件夹
    for device_folder in os.listdir(source_path):
        device_path = source_path / device_folder

        if not os.path.isdir(device_path):
            continue

        # 确定设备所属系列
        brand, series = get_device_series(device_folder)

        # 创建目标路径
        brand_path = target_path / f"{brand}系列"
        series_path = brand_path / series

        # 创建品牌和系列目录
        brand_path.mkdir(parents=True, exist_ok=True)
        series_path.mkdir(parents=True, exist_ok=True)

        # 移动设备文件夹
        target_device_path = series_path / device_folder

        if target_device_path.exists():
            print(f"⏩ 跳过已存在的设备: {device_folder}")
            continue

        try:
            shutil.move(str(device_path), str(target_device_path))
            undo_data.append({
                'device': device_folder,
                'src': str(device_path),
                'dst': str(target_device_path),
                'brand': brand,
                'series': series
            })
            print(f"✅ 已整理 {brand}系列/{series}/{device_folder}")
        except Exception as e:
            print(f"❌ 整理失败: {device_folder} - {str(e)}")

    # 写入撤销日志
    if undo_data:
        with open(CONFIG['undo_log'], 'w') as f:
            json.dump(undo_data, f, indent=2)
        print(f"\n操作已记录到 {CONFIG['undo_log']}")
    else:
        print("\n没有设备需要整理")


def undo_organization():
    """撤销整理操作"""
    if not os.path.exists(CONFIG['undo_log']):
        print("没有可撤销的操作记录")
        return

    try:
        with open(CONFIG['undo_log'], 'r') as f:
            undo_data = json.load(f)
    except Exception as e:
        print(f"读取日志失败: {str(e)}")
        return

    restored_devices = 0

    for record in reversed(undo_data):
        try:
            # 移动设备文件夹回原位置
            shutil.move(record['dst'], record['src'])
            restored_devices += 1
            print(f"↩️ 已还原 {record['device']}")

            # 如果系列文件夹为空，则删除
            series_path = Path(record['dst']).parent
            if not any(series_path.iterdir()):
                os.rmdir(series_path)
                print(f"🗑️ 已删除空系列文件夹: {series_path.name}")

            # 如果品牌文件夹为空，则删除
            brand_path = series_path.parent
            if not any(brand_path.iterdir()):
                os.rmdir(brand_path)
                print(f"🗑️ 已删除空品牌文件夹: {brand_path.name}")

        except Exception as e:
            print(f"❌ 还原失败: {record['device']} - {str(e)}")

    # 删除日志文件
    os.remove(CONFIG['undo_log'])
    print(f"\n已撤销 {restored_devices}/{len(undo_data)} 个设备整理操作")


if __name__ == "__main__":
    import sys

    print("===start,分类工具===")

    if '--undo' in sys.argv:
        print("\n正在撤销最近一次整理操作...")
        undo_organization()
        print("\n撤销操作完成！")
    else:
        print("\n开始整理设备文件夹...")
        organize_devices()
        print("\n整理操作完成！使用 --undo 参数可撤销操作")