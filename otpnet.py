import imaplib
import email
from email.header import decode_header
import html
import logging
import time
import re
from telegram import Update
from telegram.ext import Updater, CommandHandler
from telegram.error import NetworkError, TelegramError

# Thiết lập logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Thông tin cấu hình
EMAIL_ADDRESS = ""
EMAIL_PASSWORD = ""
IMAP_SERVER = ""
TELEGRAM_TOKEN = ""


def find_latest_netflix_email():
    """Tìm email chưa đọc mới nhất từ địa chỉ liên quan đến Netflix"""
    for attempt in range(3):  # Thử tối đa 3 lần
        try:
            logging.info("Checking emails...")
            mail = imaplib.IMAP4_SSL(IMAP_SERVER)
            mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            mail.select("inbox")
            _, message_numbers = mail.search(None, "UNSEEN")

            emails = []
            for num in message_numbers[0].split():
                _, msg_data = mail.fetch(num, "(RFC822)")
                email_body = msg_data[0][1]
                msg = email.message_from_bytes(email_body)
                from_ = msg.get("From")
                # Kiểm tra địa chỉ liên quan đến Netflix
                if from_ and any(domain in from_.lower() for domain in
                                 ["netflix.com", "account.netflix.com", "no-reply@netflix.com", "info@account.netflix.com"]):
                    # Lấy tiêu đề
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8", errors="replace")
                    # Lấy nội dung
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                try:
                                    body = part.get_payload(decode=True).decode(errors="replace")
                                except:
                                    body = "[Cannot decode email body]"
                                break
                    else:
                        try:
                            body = msg.get_payload(decode=True).decode(errors="replace")
                        except:
                            body = "[Cannot decode email body]"
                    # Lọc đoạn văn bản mong muốn
                    pattern = r"(Đúng, đây là tôi|Nhận mã)\s*\[https?://www\.netflix\.com/account/[^\]]*\]"
                    match = re.search(pattern, body, re.IGNORECASE)
                    filtered_body = match.group(0) if match else "[No matching text found]"

                    emails.append({
                        "from": from_,
                        "subject": subject,
                        "body": filtered_body,
                        "num": num
                    })

            mail.logout()

            if not emails:
                return None

            # Lấy email mới nhất dựa trên num
            latest_email = max(emails, key=lambda x: x["num"])
            return latest_email

        except Exception as e:
            logging.error(f"Email check attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                time.sleep(5)  # Chờ 5 giây trước khi thử lại
            else:
                return None


def find_command(update: Update, context):
    """Xử lý lệnh /find: Tìm email chưa đọc mới nhất từ Netflix"""
    chat_id = update.effective_chat.id
    logging.info(f"Received /find command from chat_id: {chat_id}")

    for attempt in range(3):  # Thử gửi tin nhắn tối đa 3 lần
        try:
            latest_email = find_latest_netflix_email()

            if latest_email:
                escaped_from = html.escape(str(latest_email["from"]))
                escaped_subject = html.escape(str(latest_email["subject"]))
                escaped_body = html.escape(str(latest_email["body"]))
                message = (
                    f"{escaped_body}"
                )
                context.bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")
                logging.info("Sent latest email info to Telegram")
            else:
                context.bot.send_message(
                    chat_id=chat_id,
                    text="No unread emails from Netflix found.",
                    parse_mode="HTML"
                )
                logging.info("No matching emails found")
            return

        except (NetworkError, TelegramError) as e:
            logging.error(f"Send attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                time.sleep(5)  # Chờ 5 giây trước khi thử lại
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            break

    context.bot.send_message(
        chat_id=chat_id,
        text="Failed to process /find command due to network issues. Please try again later.",
        parse_mode="HTML"
    )
    logging.error("Failed to send message after 3 attempts")


def main():
    """Khởi động bot Telegram"""
    logging.info("Starting bot...")
    for attempt in range(3):  # Thử khởi động bot tối đa 3 lần
        try:
            updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
            dp = updater.dispatcher
            dp.add_handler(CommandHandler("find", find_command))
            updater.start_polling()
            updater.idle()
            return

        except (NetworkError, TelegramError) as e:
            logging.error(f"Start attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                time.sleep(10)  # Chờ 10 giây trước khi thử lại
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            break

    logging.error("Failed to start bot after 3 attempts")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Main loop error: {e}")
