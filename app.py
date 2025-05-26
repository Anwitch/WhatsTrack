from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import json
import gspread
from google.oauth2.service_account import Credentials
import os
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env file

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

creds_json = os.environ.get('GOOGLE_CREDENTIALS')
if not creds_json:
    raise Exception("Environment variable GOOGLE_CREDENTIALS belum di-set!")

credentials_dict = json.loads(creds_json)

credentials = Credentials.from_service_account_info(
    credentials_dict,
    scopes=SCOPES
)

gc = gspread.authorize(credentials)
sh = gc.open("Pengeluaran")
worksheet = sh.sheet1

def tambah_pengeluaran(kategori, harga, keterangan):
    from datetime import datetime
    worksheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        kategori,
        harga,
        keterangan
    ])

app = Flask(__name__)

@app.route('/')
def home():
    return "WhatsTrack Bot is running!"

@app.route("/webhook", methods=['POST'])
def webhook():
    incoming_msg = request.values.get('Body', '').strip()
    resp = MessagingResponse()
    msg = resp.message()

    parts = incoming_msg.split(' ', 2)
    if len(parts) >= 2 and parts[1].isdigit():
        kategori = parts[0]
        harga = int(parts[1])
        keterangan = parts[2] if len(parts) == 3 else ''
        tambah_pengeluaran(kategori, harga, keterangan)
        msg.body(f"✅ Pengeluaran '{kategori}' sebesar Rp{harga} dicatat!")
    else:
        msg.body("Format salah. Contoh: makan 25000 nasi goreng")

    return str(resp)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)