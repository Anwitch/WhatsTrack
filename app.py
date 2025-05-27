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

from collections import defaultdict
from datetime import datetime

def laporan_pengeluaran_harian():
    data = worksheet.get_all_values()
    header = data[0]
    rows = data[1:]

    tanggal_idx = header.index("Tanggal & Waktu")
    harga_idx = header.index("Harga")

    total_per_tanggal = defaultdict(int)

    for row in rows:
        try:
            tanggal_str = row[tanggal_idx]
            harga_str = row[harga_idx]

            tanggal = datetime.strptime(tanggal_str, "%Y-%m-%d %H:%M:%S").date()
            harga = int(harga_str)

            total_per_tanggal[tanggal] += harga
        except Exception as e:
            print("Skip row due to error:", e)
            continue

    hasil = "📊 Laporan Pengeluaran Harian:\n"
    for tanggal, total in sorted(total_per_tanggal.items(), reverse=True):
        hasil += f"- {tanggal}: Rp{total:,}\n"

    return hasil.strip()


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
    Kamu adalah asisten pencatat keuangan.
    Tugasmu adalah membaca kalimat dan mengeluarkan hasil dalam format CSV (comma separated values) tanpa penjelasan.
    Format CSV:
    kategori,harga,keterangan

    Ketentuan:
    - kategori: jenis pengeluaran seperti makan, minum, transport, hiburan, dll
    - harga: angka bulat dalam satuan rupiah tanpa simbol atau pemisah (contoh: 15000)
    - keterangan: boleh kosong, tetapi jika ada tambahan deskripsi (misalnya "kopi" atau "ayam geprek") masukkan di sini.

    Contoh:
    Kalimat input: "tadi makan mie ayam 15 ribu"
    Jawaban: makan,15000,mie ayam

    Kalimat inputnya adalah: "{text}"
    Jawaban:
    """
    
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "mistralai/mistral-7b-instruct:free",
            "messages": [
                {"role": "system", "content": "Kamu adalah asisten pencatat keuangan."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0,
            "max_tokens": 60
        }
        
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload)
        print("Response status:", response.status_code)
        print("Response text:", response.text)
        response.raise_for_status()
        result = response.json()
        
        ai_response = result['choices'][0]['message']['content'].strip()
        ai_response = ai_response.replace('"', '').replace("'", "")
        print("OpenRouter response:", ai_response)

        parts = [x.strip() for x in ai_response.split(',', 2)]
        if len(parts) < 2:
            raise ValueError("Format hasil tidak sesuai, kurang dari 2 bagian")
        kategori = parts[0].strip().capitalize()
        harga_raw = parts[1].strip()

        def ubah_ke_angka(text):
            text = text.lower().replace('.', '').replace(' ', '')
            if 'ribu' in text:
                return int(float(text.replace('ribu', ''))) * 1000
            else:
                return int(text)

        harga = ubah_ke_angka(harga_raw)
        keterangan = parts[2].strip().title() if len(parts) == 3 else ''

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

    if "laporan" in incoming_msg and "harian" in incoming_msg:
        laporan = laporan_pengeluaran_harian()
        msg.body(laporan)
    else:
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