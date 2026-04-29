from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import *
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import json

app = Flask(__name__)

# 🔑 LINE
LINE_CHANNEL_ACCESS_TOKEN = "6TkhaYcTWrBigEH5OH5e6jez1q1kb4xS4WDKm9cO8C3gm+HPjjTKg8p4exPG7Sn3hNF0PLoL3er4PGLISnKYjeUKeRkYOSsxlKOnxlS3Kwu8pv4pN2bEiMVJLEpv0k9+ne34cno+K0jVVkCY7wlthwdB04t89/1O/w1cDnyilFU="
LINE_CHANNEL_SECRET = "299bf9cb9a1a471623ed268694416c2e"

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 🔗 Google Sheets
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("TeachingRecords").sheet1


# ===== Webhook =====
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    handler.handle(body, signature)
    return 'OK'


# ===== Main =====
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    data = sheet.get_all_values()

    # 🔴 ===== ลบข้อมูล =====
    if text.startswith("ลบ"):
        name_to_delete = text.replace("ลบ", "", 1).strip()

        rows_to_delete = []

        for i, row in enumerate(data):
            if len(row) > 0 and row[0].strip() == name_to_delete:
                rows_to_delete.append(i + 1)

        if rows_to_delete:
            for row_index in reversed(rows_to_delete):
                sheet.delete_rows(row_index)

            reply = f"ลบ {name_to_delete} {len(rows_to_delete)} รายการแล้ว ✅"
        else:
            reply = f"ไม่พบชื่อ {name_to_delete}"

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply)
        )
        return


    # 📅 ===== เลือกวัน (ชื่อ + วันที่) =====
    parts = text.split()
    if len(parts) == 2:
        search_name, search_date = parts

        result = []

        for row in data[1:]:
            if len(row) >= 4:
                if row[0].strip() == search_name and row[1].strip() == search_date:
                    result.append(f"{row[0]} | {row[1]} | {row[2]} | {row[3]}")

        reply = "\n".join(result) if result else "ไม่พบข้อมูล"

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply)
        )
        return


    # 🔍 ===== ค้นหา (ชื่อ → แสดงวันที่) =====
    dates = []
    search_name = text.strip()

    for row in data[1:]:
        if len(row) >= 2 and row[0].strip() == search_name:
            date = row[1].strip()
            if date not in dates:
                dates.append(date)

    if dates:
        quick_buttons = [
            QuickReplyButton(
                action=MessageAction(label=d, text=f"{search_name} {d}")
            )
            for d in dates
        ]

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=f"พบข้อมูลของ {search_name} เลือกวันที่:",
                quick_reply=QuickReply(items=quick_buttons)
            )
        )
        return


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
                text="พิมพ์แบบนี้:\n\nชื่อ\n\nเนื้อหา\n\nความคิดเห็น\n\nหรือ\nลบ ชื่อ\n\nหรือพิมพ์ชื่อเพื่อค้นหา"
            )
        )

# ===== Run =====
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
