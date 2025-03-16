import os
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import shutil
from concurrent.futures import ThreadPoolExecutor

# Thay thế bằng đường dẫn thực tế
source_folder = 'checked'
checked_folder = 'checked-but-member'
non_checked_folder = 'non-checked'

# Tạo thư mục đích nếu chưa tồn tại
if not os.path.exists(checked_folder):
    os.makedirs(checked_folder)
if not os.path.exists(non_checked_folder):
    os.makedirs(non_checked_folder)

# Cài đặt Chrome với profile có extension Cookie Editor
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Chạy trong chế độ ẩn
options.add_argument("--disable-gpu")  # Tắt GPU để tăng hiệu suất
options.add_argument(
    "/Users/entikayyyyy/Library/Application Support/Google/Chrome/Default")  # Thay thế bằng đường dẫn đến profile Chrome của bạn


def create_driver():
    return webdriver.Chrome(options=options)


# Hàm thêm cookies bằng JavaScript
def add_cookies(driver, json_data):
    script = """
    function importCookiesFromJSON(jsonData) {
    const cookies = JSON.parse(jsonData).cookies;
    cookies.forEach(cookie => {
        const cookieString = `${cookie.name}=${cookie.value}; path=${cookie.path}; domain=${cookie.domain}; secure=${cookie.secure}; expires=${new Date(cookie.expires * 1000).toUTCString()}`;
        document.cookie = cookieString;
    });
    }

    // Dữ liệu cookies JSON của bạn
    const jsonData = `
    """ + json_data + """
    `;

    importCookiesFromJSON(jsonData);
    """
    driver.execute_script(script)


def process_file(json_file_path):
    driver = create_driver()

    # Mở trang web
    driver.get("https://www.spotify.com/tr-en/account/manage-your-plan/")

    # Đọc dữ liệu JSON
    with open(json_file_path, 'r') as f:
        json_data = f.read()

    # Thêm cookies
    add_cookies(driver, json_data)

    # Tải lại trang
    driver.refresh()

    # Kiểm tra nội dung trang
    try:
        plan_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "your-plan"))
        )
        if 'Premium' in plan_element.text:
            print(f"Tìm thấy 'Premium' trong file {os.path.basename(json_file_path)}.")
            shutil.move(json_file_path, checked_folder)
        else:
            print(f"Không tìm thấy 'Premium' trong file {os.path.basename(json_file_path)}.")
            shutil.move(json_file_path, non_checked_folder)
    except Exception as e:
        print(f"Lỗi khi kiểm tra trang: {e}")
        shutil.move(json_file_path, non_checked_folder)

    driver.quit()


# Đọc tất cả file JSON trong thư mục nguồn
json_files = [os.path.join(source_folder, filename) for filename in os.listdir(source_folder) if
              filename.endswith('.json')]

# Chạy đa luồng
with ThreadPoolExecutor(max_workers=5) as executor:
    executor.map(process_file, json_files)
