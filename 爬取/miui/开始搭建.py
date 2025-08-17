import os
import zipfile
import subprocess
import aiofiles
import shutil
from pathlib import Path
import shlex
import re
import urllib.parse
from payload_dumper.http_file import HttpFile

# 常量定义
PROCESSED_URLS_FILE = r"processed_urls.txt"
# 修改为多个分区
DEFAULT_PARTITIONS = "boot,init_boot"  # 添加需要的分区
payload_dumper_path = ".\payload_dumper.exe"


def extract_version_from_url(url):
    """从URL中提取版本信息"""
    parsed = urllib.parse.urlparse(url)
    # 获取路径部分
    path = parsed.path
    # 分割路径
    parts = path.strip('/').split('/')

    # 尝试从路径中找到版本部分
    for part in parts:
        if re.match(r'^[A-Za-z0-9._]+$', part) and not part.endswith('.zip'):
            return part

    # 如果找不到合适的部分，使用文件名中的版本
    filename = os.path.basename(path)
    if filename.endswith('.zip'):
        filename = filename[:-4]

    # 尝试从文件名中提取版本
    version_match = re.search(r'(V\d+\.\d+\.\d+\.\d+\.[A-Z]+|[A-Z]+\d+\.\d+)', filename)
    if version_match:
        return version_match.group(0)

    # 如果还是找不到，使用最后一个非空部分
    return parts[-1] if parts else "unknown_version"


def sanitize_path_name(name):
    """清理路径名称，替换无效字符"""
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in invalid_chars:
        name = name.replace(char, '_')
    return name.strip()


async def load_device_info_from_file(file_path):
    try:
        devices = []
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
            async for line in file:
                line = line.strip()
                if not line:
                    continue
                # 提取格式 "设备: xxx, 版本: xxx, 链接: xxx"
                if "设备:" in line and "版本:" in line and "链接:" in line:
                    parts = line.split(",")
                    name_part = parts[0].split(":")[1].strip()
                    version_part = parts[1].split(":")[1].strip()
                    link_part = parts[2].split(":")[1].strip()
                    devices.append((name_part, version_part, link_part))
        return devices
    except Exception as e:
        print(f"加载设备文件失败：{e}")
        return []


async def load_processed_urls():
    if os.path.exists(PROCESSED_URLS_FILE):
        async with aiofiles.open(PROCESSED_URLS_FILE, 'r', encoding='utf-8') as file:
            return set(line.strip() for line in await file.readlines())
    return set()


async def save_processed_url(url):
    print(f"记录链接：{url}")  # 调试输出
    async with aiofiles.open(PROCESSED_URLS_FILE, 'a', encoding='utf-8') as file:
        await file.write(url + "\n")


async def extract_partition_from_zip(file, output_dir, partitions, version_identifier, device_name):
    try:
        with zipfile.ZipFile(file) as z:
            file_list = z.namelist()
            # 使用原始设备名称作为文件夹名（仅清理无效字符）
            sanitized_name = sanitize_path_name(device_name)
            found_partitions = set()

            # 收集所有找到的分区
            for partition in partitions.split(","):
                partition_files = [f for f in file_list if f.endswith(f"{partition}.img")]
                if partition_files:
                    found_partitions.add(partition)

            # 只处理找到的分区
            for partition in found_partitions:
                # 使用原始设备名称作为文件夹名
                target_dir = Path(output_dir) / sanitized_name / partition
                target_dir.mkdir(parents=True, exist_ok=True)

                partition_files = [f for f in file_list if f.endswith(f"{partition}.img")]
                for partition_file in partition_files:
                    # 使用URL中的版本信息作为文件名前缀
                    output_path = target_dir / f"{version_identifier}_{partition}.img"
                    with z.open(partition_file) as src, open(output_path, "wb") as dest:
                        dest.write(src.read())
                    print(f"提取完成：{partition_file} -> {output_path}")

            # 打印未找到的分区
            not_found = set(partitions.split(",")) - found_partitions
            if not_found:
                print(f"在ZIP中未找到分区: {', '.join(not_found)}")

    except zipfile.BadZipFile:
        print(f"无效的 ZIP 文件：{file}")


async def check_for_payload_bin(file):
    """
    检查 ZIP 文件中是否包含 payload.bin。
    """
    try:
        with zipfile.ZipFile(file) as z:
            return "payload.bin" in z.namelist()
    except zipfile.BadZipFile:
        print(f"无效的 ZIP 文件：{file}")
        return False


async def extract_partitions(partitions, source, version_identifier, device_name):
    """
    使用 payload_dumper 提取分区。
    """
    base_dir = Path(os.getcwd())
    # 使用原始设备名称作为文件夹名
    sanitized_name = sanitize_path_name(device_name)
    default_output_dir = base_dir / "output"
    found_partitions = []

    try:
        subprocess.run(["payload_dumper", "--partitions", partitions, str(source)], check=True)

        # 检查哪些分区被成功提取
        for partition in partitions.split(","):
            partition_file = default_output_dir / f"{partition}.img"
            if partition_file.exists():
                found_partitions.append(partition)

        # 只处理找到的分区
        for partition in found_partitions:
            partition_file = default_output_dir / f"{partition}.img"
            # 使用原始设备名称作为文件夹名
            target_dir = base_dir / sanitized_name / partition
            target_dir.mkdir(parents=True, exist_ok=True)
            # 使用URL中的版本信息作为文件名前缀
            renamed_file = target_dir / f"{version_identifier}_{partition}.img"
            shutil.move(str(partition_file), str(renamed_file))
            print(f"成功提取：{partition_file} -> {renamed_file}")

        # 打印未找到的分区
        not_found = set(partitions.split(",")) - set(found_partitions)
        if not_found:
            print(f"未找到分区文件: {', '.join(not_found)}")

        shutil.rmtree(str(default_output_dir), ignore_errors=True)

    except subprocess.CalledProcessError as e:
        print(f"分区提取失败：{e}")
    except Exception as e:
        print(f"提取过程中发生错误：{e}")


async def process_recovery_package(url, version_identifier, device_name, partitions=DEFAULT_PARTITIONS):
    try:
        with HttpFile(url) as file:
            if await check_for_payload_bin(file):
                await extract_partitions(partitions, url, version_identifier, device_name)
            else:
                await extract_partition_from_zip(file, os.getcwd(), partitions, version_identifier, device_name)
    except Exception as e:
        print(f"处理失败：{e}")


def load_device_list(file_path):
    devices = []
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        for line in lines:
            # 用正则表达式匹配设备、版本和链接信息
            match = re.match(r"设备:\s*(.*),\s*版本:\s*(.*),\s*链接:\s*(https?://.*)", line.strip())
            if match:
                # 直接使用设备名称，不进行额外处理
                device_name = match.group(1).strip()
                version = match.group(2).strip()
                url = match.group(3).strip()
                devices.append((device_name, version, url))
            else:
                print(f"跳过无效的行: {line.strip()}")
    return devices


async def process_device(device_name, version, url):
    processed_urls = await load_processed_urls()

    # 输出接收到的 URL，便于调试
    print(f"接收到的链接：{url}")

    # 校验 URL 是否包含 http:// 或 https://
    if not re.match(r'^https?://', url):
        print(f"跳过无效的链接：{url}")
        return

    if url in processed_urls:
        print(f"跳过已处理的链接：{url}")
        return

    # 从URL中提取版本标识符
    version_identifier = extract_version_from_url(url)
    print(f"从URL提取的版本标识: {version_identifier}")

    print(f"处理卡刷包：{url} （设备：{device_name}）")
    await process_recovery_package(url, version_identifier, device_name)
    await save_processed_url(url)


async def main():
    file_path = input("请输入设备列表 TXT 文件路径：")
    print(f"从文件加载设备列表：{file_path}")

    # 加载设备列表
    devices = load_device_list(file_path)
    if not devices:
        print("未找到有效的设备数据。")
        return

    for device_name, version, url in devices:
        await process_device(device_name, version, url)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
