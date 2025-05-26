from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

import gspread
from google.oauth2.service_account import Credentials

import os
# Inisialisasi Google Sheets
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
credentials = Credentials.from_service_account_file(
    'Credentials/whatstrack-460713-818ce75f167c.json',
    scopes=SCOPES
)
gc = gspread.authorize(credentials)
sh = gc.open("Pengeluaran")
worksheet = sh.sheet1

# Contoh fungsi untuk menambah data
def tambah_pengeluaran(kategori, harga, keterangan):
    from datetime import datetime
    worksheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        kategori,
        harga,
        keterangan
    ])

app = Flask(__name__)

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
    app.run(host='0.0.0.0', port=port, debug=True)
