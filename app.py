from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import json
import gspread
from google.oauth2.service_account import Credentials
import os
from dotenv import load_dotenv
import openai
load_dotenv()  # load environment variables from .env file
openai.api_key = os.environ.get("OPENAI_API_KEY")


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
    Tugasmu adalah mengambil informasi dari kalimat berikut dan mengubahnya ke format CSV: kategori, harga (angka saja, tanpa Rp atau titik), keterangan.
    Kalimat: "{text}"
    Jawaban (format: kategori, harga, keterangan):
    """
    try:
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt,
            temperature=0,
            max_tokens=60
        )
        result = response.choices[0].text.strip()

        print("OpenAI response:", result)

        kategori, harga, keterangan = [x.strip() for x in result.split(',', 2)]
        return kategori, int(harga), keterangan
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