import telebot
import os
import yt_dlp
import fitz
import time
from groq import Groq
from youtube_transcript_api import YouTubeTranscriptApi
from PIL import Image
import threading
import http.server
import socketserver

# --- KONFIGURASI ---
TOKEN = '8411809165:AAEY_6CfQwAVO4zag2S-iwiKFluG9R8Ky8Y'
GROQ_API_KEY = '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'
ADMIN_ID = 1408120389

# Gunakan threaded=False untuk menghemat penggunaan thread di server kecil
bot = telebot.TeleBot(TOKEN, threaded=False)
client = Groq(api_key=GROQ_API_KEY)

# Server minimalis untuk Koyeb
def run_server():
    try:
        handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", 8000), handler) as httpd:
            httpd.serve_forever()
    except: pass

threading.Thread(target=run_server, daemon=True).start()

# --- FUNGSI OPTIMAL ---
def kirim_log(user, aksi):
    try:
        nama = user.first_name or "User"
        bot.send_message(ADMIN_ID, f"🔔 LOG: {nama} -> {aksi}")
    except: pass

def get_ai_response(prompt):
    try:
        chat = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}]
        )
        return chat.choices[0].message.content
    except:
        return "⚠️ Layanan AI sibuk."

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, "Bot Aktif. Silakan kirim pesan atau link.")
    kirim_log(message.from_user, "Start")

@bot.message_handler(content_types=['photo', 'document'])
def handle_files(message):
    uid = message.chat.id
    try:
        if message.content_type == 'photo':
            file_info = bot.get_file(message.photo[-1].file_id)
            down = bot.download_file(file_info.file_path)
            img_p, pdf_p = f"i_{uid}.jpg", f"o_{uid}.pdf"
            with open(img_p, "wb") as f: f.write(down)
            Image.open(img_p).convert('RGB').save(pdf_p)
            with open(pdf_p, 'rb') as f: bot.send_document(uid, f)
            os.remove(img_p); os.remove(pdf_p)
        elif message.document.file_name.lower().endswith('.pdf'):
            file_info = bot.get_file(message.document.file_id)
            path = f"t_{uid}.pdf"
            with open(path, "wb") as f: f.write(bot.download_file(file_info.file_path))
            doc = fitz.open(path)
            for i in range(len(doc)):
                img = f"{uid}_{i}.jpg"
                doc.load_page(i).get_pixmap().save(img)
                with open(img, 'rb') as f: bot.send_photo(uid, f)
                os.remove(img)
            doc.close(); os.remove(path)
    except: bot.reply_to(message, "Gagal memproses.")

@bot.message_handler(func=lambda m: m.text and m.text.startswith('http'))
def handle_links(message):
    url, uid = message.text, message.chat.id
    if "youtube.com" in url or "youtu.be" in url:
        try:
            vid = url.split("v=")[1].split("&")[0] if "v=" in url else url.split("/")[-1]
            ts = YouTubeTranscriptApi.get_transcript(vid, languages=['id', 'en'])
            txt = " ".join([t['text'] for t in ts])
            bot.reply_to(message, get_ai_response(f"Ringkas: {txt[:4000]}"))
            return
        except: pass
    
    try:
        opts = {'format': 'best[height<=480]', 'outtmpl': f"v_{uid}.%(ext)s", 'quiet': True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            fname = ydl.prepare_filename(info)
            with open(fname, 'rb') as f: bot.send_video(uid, f)
            os.remove(fname)
    except: bot.reply_to(message, "Gagal download.")

@bot.message_handler(func=lambda m: True)
def handle_ai(message):
    bot.reply_to(message, get_ai_response(message.text))

# --- ANTI-CONFLICT & LIGHTWEIGHT RUN ---
if __name__ == "__main__":
    bot.remove_webhook()
    time.sleep(1)
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=20)
        except:
            time.sleep(5)
