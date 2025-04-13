import imaplib
import email
from email.header import decode_header
import html
import logging
import time
from telegram.ext import Updater, CommandHandler
from telegram import Update
from telegram.error import NetworkError, TelegramError

# Thiết lập logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# Thông tin cấu hình
EMAIL_ADDRESS = "banamahoot@gmail.com"  # Thay bằng email của bạn
EMAIL_PASSWORD = "lptk mngb htte lwkz"    # Thay bằng mật khẩu ứng dụng
IMAP_SERVER = "imap.gmail.com"
TELEGRAM_TOKEN = "7894223540:AAGFGsXnrc8ZnarRi3Db3SRakdqrVcaB-64"  # Thay bằng token từ BotFather
CHAT_ID = "1291042032"       # Thay bằng ID Telegram của bạn


def find_latest_openai_email():
    """Tìm email chưa đọc mới nhất từ địa chỉ chứa 'openai'"""
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
                if from_ and "openai" in from_.lower():
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
                    emails.append({
                        "from": from_,
                        "subject": subject,
                        "body": body,
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
    """Xử lý lệnh /find: Tìm email chưa đọc mới nhất từ openai"""
    chat_id = update.effective_chat.id
    logging.info(f"Received /find command from chat_id: {chat_id}")

    for attempt in range(3):  # Thử gửi tin nhắn tối đa 3 lần
        try:
            latest_email = find_latest_openai_email()

            if latest_email:
                escaped_from = html.escape(str(latest_email["from"]))
                escaped_subject = html.escape(str(latest_email["subject"]))
                escaped_body = html.escape(latest_email["body"][:1000])  # Giới hạn độ dài
                message = (
                    f"<b>Subject:</b> {escaped_subject}\n\n"
                )
                context.bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")
                logging.info("Sent latest email info to Telegram")
            else:
                context.bot.send_message(
                    chat_id=chat_id,
                    text="No unread emails from 'openai' found.",
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
            updater = Updater(TELEGRAM_TOKEN, use_context=True)
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