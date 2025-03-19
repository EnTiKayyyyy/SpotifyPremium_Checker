import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import tkinter as tk
from tkinter import filedialog, messagebox

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options

# ------------------------------------------------------------------------------------
# CÁC HẰNG SỐ VỀ SPOTIFY VÀ XPATH
# ------------------------------------------------------------------------------------
LOGIN_URL = (
    "https://accounts.spotify.com/vi/login?allow_password=1"
    "&continue=https%3A%2F%2Fwww.spotify.com%2Ftr-en%2Faccount%2Fmanage-your-plan%2F"
)

ERROR_MESSAGE_XPATH = "//span[text()='Tên người dùng hoặc mật khẩu không chính xác.']"
PLAN_XPATH = '//*[@id="your-plan"]/section/div/div[1]/div/div/div[2]/span'
EXPIRY_XPATH = '//*[@id="your-plan"]/section/div/div[2]/div/div[2]/div[2]/div/div[1]/b[2]'
ALT_EXPIRY_XPATH = '//*[@id="your-plan"]/section/div/div[2]/div/div[2]/div/div/div[1]/b[2]'


def process_account(line: str) -> str:
    """
    Xử lý đăng nhập + lấy thông tin 1 tài khoản (username:password).
    Trả về chuỗi kết quả để ghi vào file hoặc hiển thị.
    """
    line = line.strip()
    if not line:
        return "Dòng trống / Không hợp lệ"

    # Tách username/password
    try:
        username, password = line.split(":")
    except ValueError:
        return f"{line} => Sai định dạng (không phải username:password)"

    # Khởi tạo trình duyệt (Chrome).
    # Nếu cần chỉ định chromedriver, bạn có thể:
    # driver = webdriver.Chrome(executable_path="path/to/chromedriver")
    # hoặc dùng webdriver_manager...
    chrome_options = Options()
    chrome_options.add_argument("--headless")       # Chạy ẩn (không cửa sổ)
    chrome_options.add_argument("--disable-gpu")    # (Khuyên dùng cho Windows cũ)
    driver = webdriver.Chrome(options=chrome_options)

    try:
        wait = WebDriverWait(driver, 2)

        # 1) Truy cập trang login
        driver.get(LOGIN_URL)
        time.sleep(2)  # Đợi trang load (tuỳ chỉnh)

        # 2) Điền thông tin đăng nhập
        try:
            username_field = driver.find_element(By.ID, "login-username")
            username_field.clear()
            username_field.send_keys(username)

            password_field = driver.find_element(By.ID, "login-password")
            password_field.clear()
            password_field.send_keys(password)

            login_button = driver.find_element(By.ID, "login-button")
            login_button.click()
        except Exception as e:
            return f"{username}:{password} => Lỗi thao tác login: {e}"

        # 3) Kiểm tra lỗi đăng nhập
        time.sleep(3)  # Chờ trang xử lý đăng nhập

        is_invalid = False
        try:
            short_wait = WebDriverWait(driver, 2)
            short_wait.until(EC.presence_of_element_located((By.XPATH, ERROR_MESSAGE_XPATH)))
            # Nếu không Timeout ⇒ tìm thấy element báo lỗi
            is_invalid = True
        except TimeoutException:
            pass  # Không thấy => có thể đăng nhập thành công

        if is_invalid:
            return f"{username}:{password} => Invalid"
        else:
            # 4) Đăng nhập thành công => Lấy thông tin plan
            plan = "Không thể lấy thông tin plan"
            expiry = "Không rõ"

            # Lấy plan
            try:
                plan_element = wait.until(
                    EC.visibility_of_element_located((By.XPATH, PLAN_XPATH))
                )
                plan = plan_element.text
            except (TimeoutException, NoSuchElementException):
                plan = "Không thể lấy thông tin plan"

            # Lấy expiry
            try:
                expiry_element = WebDriverWait(driver, 4).until(
                    EC.presence_of_element_located((By.XPATH, EXPIRY_XPATH))
                )
                expiry = expiry_element.text
            except TimeoutException:
                # Thử xpath thay thế
                try:
                    expiry_element_alt = driver.find_element(By.XPATH, ALT_EXPIRY_XPATH)
                    expiry = expiry_element_alt.text
                except:
                    expiry = "Không rõ"
            except NoSuchElementException:
                expiry = "Không rõ"
            except Exception as e:
                expiry = f"Lỗi khác: {e}"

            return f"{username}:{password} => Plan: {plan}, Expiry: {expiry}"

    finally:
        # Đóng trình duyệt
        driver.quit()


def run_check_accounts(input_file: str, output_file: str, max_workers: int, log_callback=None):
    """
    - Đọc file input -> Đa luồng chạy process_account.
    - Ghi kết quả vào file output.
    - log_callback(msg) để hiển thị log lên GUI (nếu có).
    """
    # Đọc tất cả các dòng
    with open(input_file, "r", encoding="utf-8") as f_in:
        lines = [line.strip() for line in f_in if line.strip()]

    # Mở file kết quả
    with open(output_file, "w", encoding="utf-8") as f_out:
        # Tạo ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_account, line): line for line in lines}

            for future in as_completed(futures):
                account_line = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    result = f"{account_line} => Lỗi ngoại lệ: {exc}"

                # Ghi file & log
                f_out.write(result + "\n")
                if log_callback:
                    log_callback(result)


# ------------------------------------------------------------------------------------
# PHẦN GIAO DIỆN TKINTER
# ------------------------------------------------------------------------------------
def select_input_file():
    """Hàm gọi hộp thoại chọn file TXT, lưu vào biến file_path."""
    file_selected = filedialog.askopenfilename(
        title="Chọn file .txt chứa username:password",
        filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
    )
    if file_selected:
        file_path.set(file_selected)


def start_check():
    """
    Lấy đường dẫn input, số luồng => gọi hàm run_check_accounts trong 1 thread,
    tránh chặn GUI.
    """
    selected_file = file_path.get()
    if not selected_file:
        messagebox.showwarning("Cảnh báo", "Vui lòng chọn file TXT chứa tài khoản!")
        return

    # Mặc định file output = "results.txt" cùng thư mục file input
    base_dir = os.path.dirname(selected_file)
    output_file = os.path.join(base_dir, "results.txt")

    # Lấy số luồng từ Spinbox
    try:
        threads = int(num_threads.get())
        if threads < 1:
            raise ValueError
    except ValueError:
        messagebox.showwarning("Cảnh báo", "Số luồng không hợp lệ! Phải là số nguyên dương.")
        return

    # Khóa nút (tránh bấm nhiều lần)
    btn_run.config(state=tk.DISABLED)

    # Hàm chạy ngầm
    def worker():
        # In ra GUI
        append_log(f"Bắt đầu kiểm tra. Input: {selected_file}, Output: {output_file}, Threads={threads}")
        start_time = time.time()

        run_check_accounts(selected_file, output_file, threads, log_callback=append_log)

        end_time = time.time()
        append_log(f"Hoàn thành sau {end_time - start_time:.2f} giây. Kết quả lưu tại {output_file}")

        # Hiện thông báo pop-up
        messagebox.showinfo("Hoàn thành", "Quá trình kiểm tra đã kết thúc!")
        # Mở lại nút
        btn_run.config(state=tk.NORMAL)

    # Tạo thread để không chặn GUI
    t = threading.Thread(target=worker)
    t.start()


def append_log(msg: str):
    """Thêm dòng log vào Text widget."""
    text_area.insert(tk.END, msg + "\n")
    text_area.see(tk.END)


# ------------------------------------------------------------------------------------
# TẠO CỬA SỔ CHÍNH
# ------------------------------------------------------------------------------------
root = tk.Tk()
root.title("Kiểm tra tài khoản Spotify")

# Biến lưu đường dẫn file input
file_path = tk.StringVar()
# Biến lưu số luồng
num_threads = tk.StringVar(value="5")  # mặc định 5

# Frame chọn file
frame_file = tk.Frame(root)
frame_file.pack(padx=10, pady=5, fill="x")

lbl_file = tk.Label(frame_file, text="File input (.txt):")
lbl_file.pack(side=tk.LEFT)

entry_file = tk.Entry(frame_file, textvariable=file_path, width=50)
entry_file.pack(side=tk.LEFT, padx=5)

btn_browse = tk.Button(frame_file, text="Chọn...", command=select_input_file)
btn_browse.pack(side=tk.LEFT)

# Frame chọn số luồng
frame_threads = tk.Frame(root)
frame_threads.pack(padx=10, pady=5, fill="x")

lbl_threads = tk.Label(frame_threads, text="Số luồng:")
lbl_threads.pack(side=tk.LEFT)

spin_threads = tk.Spinbox(frame_threads, from_=1, to=100, textvariable=num_threads, width=5)
spin_threads.pack(side=tk.LEFT, padx=5)

# Nút "Chạy"
btn_run = tk.Button(root, text="Chạy kiểm tra", command=start_check)
btn_run.pack(pady=10)

# Khung text hiển thị log
frame_log = tk.Frame(root)
frame_log.pack(padx=10, pady=5, fill="both", expand=True)

text_area = tk.Text(frame_log, height=10)
text_area.pack(side=tk.LEFT, fill="both", expand=True)

scrollbar = tk.Scrollbar(frame_log, command=text_area.yview)
scrollbar.pack(side=tk.RIGHT, fill="y")
text_area.config(yscrollcommand=scrollbar.set)

root.mainloop()
