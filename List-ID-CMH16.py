from flask import Flask, render_template, request
import telegram
import imaplib
import email
from email.header import decode_header
import asyncio

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = "7042114081:AAEWQeB8o3_Iu1PKDxcspH9WLa1FEWYoIfI"
TELEGRAM_CHAT_ID = "-4179881222"

processed_emails = 0
total_emails = 0
list_ids_collected = 0


async def send_telegram_message(message):  # Modify to async function
    try:
        bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)  # Use await here
        print("Message sent to Telegram successfully!")
    except Exception as e:
        print(f"Error sending message to Telegram: {e}")


def process_emails(username, password, host, port):
    global processed_emails, total_emails, list_ids_collected
    try:
        list_ids_message = ""

        if port == 993:
            mail = imaplib.IMAP4_SSL(host, port)
        else:
            mail = imaplib.IMAP4(host, port)

        mail.login(username, password)
        mail.select('inbox')

        result, data = mail.search(None, 'ALL')

        if result == 'OK':
            email_ids = data[0].split()
            total_emails = len(email_ids)
            for email_id in email_ids:
                result, message_data = mail.fetch(email_id, '(RFC822 FLAGS BODY.PEEK[])')
                if result == 'OK':
                    processed_emails += 1
                    processed_percentage = (processed_emails / total_emails) * 100
                    print(f"Progress: {processed_percentage:.2f}%")

                    raw_email = message_data[0][1]
                    message = email.message_from_bytes(raw_email)
                    list_ids = message.get_all('List-Id')
                    if list_ids:
                        for list_id in list_ids:
                            decoded_list_id = decode_header(list_id)[0][0].decode() if decode_header(list_id)[0][
                                1] else list_id
                            list_ids_message += f"{decoded_list_id}\n"
                            list_ids_collected += 1
                            if list_ids_collected == 20:
                                asyncio.run(send_telegram_message(list_ids_message))  # Use asyncio.run here
                                print("List IDs sent to Telegram:", list_ids_message)
                                list_ids_message = ""
                                list_ids_collected = 0

    except Exception as e:
        print(f"Error processing emails for {username}: {e}")

    finally:
        mail.logout()


@app.route('/', methods=['GET', 'POST'])
def index():
    global processed_emails, total_emails
    if request.method == 'POST':
        processed_emails = 0
        total_emails = 0

        imap_settings = request.form['imap_settings']
        email_credentials = request.form['email_credentials']

        imap_parts = imap_settings.split(';')
        email_parts = email_credentials.split(';')

        if len(imap_parts) == 2 and len(email_parts) == 2:
            host, port = imap_parts
            email, password = email_parts

            process_emails(email, password, host, int(port))
            return render_template('list-ID.html', total_emails=total_emails, progress_percentage=100)
        else:
            return "Invalid input format. Please provide host;port for IMAP settings and email;password for email credentials."
    return render_template('list-ID.html')


if __name__ == '__main__':
    app.run(debug=True, port=5050)
