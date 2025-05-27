from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import json
import gspread
from google.oauth2.service_account import Credentials
import os
from dotenv import load_dotenv
import requests  # Menggantikan openai library dengan requests

load_dotenv()  # load environment variables from .env file

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

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

def parse_pengeluaran(text):
    prompt = f"""
    Kamu adalah asisten pencatat keuangan yang hanya menjawab dalam format CSV:
    kategori, harga (angka bulat tanpa Rp, koma, titik, atau spasi), keterangan (boleh kosong).
    Kalimat: "{text}"
    Jawaban harus persis format CSV tanpa kata lain:
    """
    
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "openchat/openchat-3.5",  # Model gratis yang tersedia di OpenRouter
            "messages": [
                {"role": "system", "content": "Kamu adalah asisten pencatat keuangan."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0,
            "max_tokens": 60
        }
        
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        
        ai_response = result['choices'][0]['message']['content'].strip()
        print("OpenRouter response:", ai_response)

        parts = [x.strip() for x in ai_response.split(',', 2)]
        if len(parts) < 2:
            raise ValueError("Format hasil tidak sesuai, kurang dari 2 bagian")
        kategori = parts[0]
        harga_raw = parts[1]

        def ubah_ke_angka(text):
            text = text.lower().replace('.', '').replace(' ', '')
            if 'ribu' in text:
                return int(float(text.replace('ribu', ''))) * 1000
            else:
                return int(text)

        harga = ubah_ke_angka(harga_raw)
        keterangan = parts[2] if len(parts) == 3 else ''

        return kategori, harga, keterangan
    except Exception as e:
        print("Parsing error:", e)
        return None, None, None

app = Flask(__name__)

@app.route('/')
def home():
    return "WhatsTrack Bot is running!"

@app.route("/webhook", methods=['POST'])
def webhook():
    incoming_msg = request.values.get('Body', '').strip()
    resp = MessagingResponse()
    msg = resp.message()

    kategori, harga, keterangan = parse_pengeluaran(incoming_msg)

    if kategori and harga:
        tambah_pengeluaran(kategori, harga, keterangan)
        msg.body(f"✅ Pengeluaran '{kategori}' sebesar Rp{harga} dicatat!\n📝 Keterangan: {keterangan}")
    else:
        msg.body("❌ Maaf, aku tidak paham inputnya. Coba tulis seperti: 'tadi makan mie ayam 15 ribu'")

    return str(resp)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)