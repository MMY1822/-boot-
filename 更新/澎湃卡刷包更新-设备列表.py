import requests
import time
import os

download_base_url = "https://bkt-sgp-miui-ota-update-alisgp.oss-ap-southeast-1.aliyuncs.com"

file_path = "澎湃_全机型卡刷包链接.txt"
output_lines = []

def extract_device_codes_from_json(url):
    response = requests.get(url)
    if response.status_code == 200:
        devices_data = response.json()
        device_codes = []
        for brand in devices_data:
            if "devices" in devices_data[brand]:
                for device in devices_data[brand]["devices"]:
                    device_code = device.get("code")
                    if device_code:
                        device_codes.append(device_code)
        return device_codes
    else:
        print("无法获取 JSON 数据，HTTP 状态码:", response.status_code)
        return []

def fetch_data_from_json(device_code, target_branch_name="小米澎湃 OS 正式版"):
    url = f"https://data.hyperos.fans/devices/{device_code}.json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        device_data = response.json()

        # 解析 JSON 数据
        device_name = device_data['name']['zh']

        found_roms = False
        for branch in device_data['branches']:
            branch_name = branch['name']['zh']
            if branch_name != target_branch_name:
                continue  # 跳过非目标分支

            found_roms = True

            for rom_version, files in branch['roms'].items():
                # 卡刷包 URL
                recovery_url = files.get('recovery')
                if recovery_url:
                    recovery_package = f"{download_base_url}/{rom_version}/{recovery_url}"
                    output_lines.append(f"设备: {device_name}, 版本: {rom_version}, 链接: {recovery_package}\n")

        if not found_roms:
            output_lines.append(f"设备: {device_name}, 未找到目标分支的 ROM 数据。\n")

        return True

    except requests.RequestException as e:
        print(f"设备代号 {device_code} 请求失败: {e}")
        return False

devices_url = "https://data.hyperos.fans/devices.json"

device_codes = extract_device_codes_from_json(devices_url)
print("提取到的设备代号数量：", len(device_codes))

start_time = time.time()
for device_code in device_codes:
    fetch_data_from_json(device_code)
end_time = time.time()


with open(file_path, 'w', encoding='utf-8') as file:
    file.writelines(output_lines)


print(f"输出已写入文件：{os.path.abspath(file_path)}")
print(f"总耗时：{end_time - start_time:.2f} 秒")