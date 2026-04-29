from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import *
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

app = Flask(__name__)

# 🔑 ใส่ของคุณตรงนี้
LINE_CHANNEL_ACCESS_TOKEN = "6TkhaYcTWrBigEH5OH5e6jez1q1kb4xS4WDKm9cO8C3gm+HPjjTKg8p4exPG7Sn3hNF0PLoL3er4PGLISnKYjeUKeRkYOSsxlKOnxlS3Kwu8pv4pN2bEiMVJLEpv0k9+ne34cno+K0jVVkCY7wlthwdB04t89/1O/w1cDnyilFU="
LINE_CHANNEL_SECRET = "299bf9cb9a1a471623ed268694416c2e"

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 🔗 เชื่อม Google Sheets
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("TeachingRecords").sheet1

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    handler.handle(body, signature)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()

    # 🔴 ===== ลบข้อมูล =====
    if text.startswith("ลบ"):
        name_to_delete = text.replace("ลบ", "").strip()

        data = sheet.get_all_values()
        rows_to_delete = []

        for i, row in enumerate(data):
            if row and row[0] == name_to_delete:
                rows_to_delete.append(i + 1)

        if rows_to_delete:
            for row_index in reversed(rows_to_delete):
                sheet.delete_rows(row_index)

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"ลบข้อมูลของ {name_to_delete} เรียบร้อย ✅")
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"ไม่พบชื่อ {name_to_delete}")
            )
        return  # 🔥 สำคัญ

    # 🟢 ===== บันทึกข้อมูล =====
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]

    if len(parts) == 3:
        name, content, comment = parts
        date = datetime.now().strftime("%Y-%m-%d")

        sheet.append_row([name, date, content, comment])

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="บันทึกเรียบร้อย ✅")
        )
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="พิมพ์แบบนี้:\n\nชื่อ\n\nเนื้อหา\n\nความคิดเห็น\n\nหรือ\nลบ ชื่อ"
            )
        )

if __name__ == "__main__":
    app.run()
