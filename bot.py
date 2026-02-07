import telebot
import os
import yt_dlp
import fitz
import docx
from groq import Groq
from youtube_transcript_api import YouTubeTranscriptApi
from PIL import Image
import threading
import http.server
import socketserver

# Konfigurasi Utama
TOKEN = '8411809165:AAEY_6CfQwAVO4zag2S-iwiKFluG9R8Ky8Y'
GROQ_API_KEY = 'Gsk_VI4KVI76xYpPPJMeeenTWGdyb3FYLnyD6SOr9Qm8qmsjkbsFwQ6N'
ADMIN_ID = 1408120389

bot = telebot.TeleBot(TOKEN)
client = Groq(api_key=GROQ_API_KEY)

# Server untuk Koyeb
def run_server():
    with socketserver.TCPServer(("", 8000), http.server.SimpleHTTPRequestHandler) as httpd:
        httpd.serve_forever()
threading.Thread(target=run_server, daemon=True).start()

def kirim_log(user, aksi):
    try:
        nama = user.first_name
        uname = f"@{user.username}" if user.username else "User"
        bot.send_message(ADMIN_ID, f"LOG: {nama} ({uname}) - {aksi}")
    except: pass

def get_ai_response(prompt):
    try:
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "system", "content": "Anda adalah asisten profesional."},
                      {"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content
    except: return "Layanan AI sedang tidak tersedia."

@bot.message_handler(commands=['start', 'help'])
def start_handler(message):
    teks = (
        "Layanan Bot Terintegrasi\n\n"
        "Fitur tersedia:\n"
        "1. AI Chat: Kirim pesan teks\n"
        "2. Ringkasan YouTube: Kirim link video YT\n"
        "3. Download Video: Kirim link media sosial\n"
        "4. Foto ke PDF: Kirim foto Anda\n"
        "5. PDF ke Gambar: Kirim file PDF\n"
        "6. Word ke Teks: Kirim file .docx"
    )
    bot.reply_to(message, teks)
    kirim_log(message.from_user, "Akses Start")

@bot.message_handler(content_types=['document'])
def document_handler(message):
    uid = message.chat.id
    try:
        file_info = bot.get_file(message.document.file_id)
        ext = message.document.file_name.split('.')[-1].lower()
        status = bot.reply_to(message, f"Memproses {ext.upper()}...")
        
        content = bot.download_file(file_info.file_path)
        path = f"tmp_{uid}.{ext}"
        with open(path, "wb") as f: f.write(content)

        if ext == 'pdf':
            doc = fitz.open(path)
            for i in range(len(doc)):
                page = doc.load_page(i)
                pix = page.get_pixmap()
                img = f"p{i}_{uid}.jpg"
                pix.save(img)
                with open(img, 'rb') as f_img:
                    bot.send_photo(uid, f_img, caption=f"Halaman {i + 1}")
                os.remove(img)
            doc.close()
            kirim_log(message.from_user, "Konversi PDF")

        elif ext == 'docx':
            d = docx.Document(path)
            txt_content = "\n".join([p.text for p in d.paragraphs])
            txt_path = f"res_{uid}.txt"
            with open(txt_path, "w") as f: f.write(txt_content)
            with open(txt_path, "rb") as f_txt:
                bot.send_document(uid, f_txt, caption="Ekstraksi teks berhasil")
            os.remove(txt_path)
            kirim_log(message.from_user, "Konversi Word")

        os.remove(path)
        bot.delete_message(uid, status.message_id)
    except: bot.reply_to(message, "Gagal memproses dokumen.")

@bot.message_handler(func=lambda m: m.text and m.text.startswith('http'))
def link_handler(message):
    url = message.text
    uid = message.chat.id

    if "youtube.com" in url or "youtu.be" in url:
        status = bot.reply_to(message, "Menganalisis video...")
        try:
            v_id = url.split("v=")[1].split("&")[0] if "v=" in url else url.split("/")[-1]
            ts = YouTubeTranscriptApi.get_transcript(v_id, languages=['id', 'en'])
            raw_text = " ".join([i['text'] for i in ts])
            summary = get_ai_response(f"Buat ringkasan poin penting: {raw_text[:5000]}")
            bot.edit_message_text(f"Ringkasan Video:\n\n{summary}", uid, status.message_id)
            kirim_log(message.from_user, "Ringkasan YT")
            return
        except:
            bot.edit_message_text("Gagal meringkas. Mencoba mengunduh video...", uid, status.message_id)
    else: status = bot.reply_to(message, "Sedang mengunduh...")

    try:
        opts = {'format': 'best[height<=720]', 'outtmpl': f'v_{uid}.%(ext)s', 'quiet': True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            fpath = ydl.prepare_filename(info)
            with open(fpath, 'rb') as v:
                bot.send_video(uid, v, caption="Unduhan selesai")
            os.remove(fpath)
            kirim_log(message.from_user, "Download Video")
        bot.delete_message(uid, status.message_id)
    except: bot.edit_message_text("Gagal memproses tautan.", uid, status.message_id)

@bot.message_handler(content_types=['photo'])
def photo_handler(message):
    try:
        info = bot.get_file(message.photo[-1].file_id)
        img_data = bot.download_file(info.file_path)
        img_p, pdf_p = f"i_{message.chat.id}.jpg", f"r_{message.chat.id}.pdf"
        with open(img_p, "wb") as f: f.write(img_data)
        Image.open(img_p).convert('RGB').save(pdf_p)
        with open(pdf_p, 'rb') as f_pdf:
            bot.send_document(message.chat.id, f_pdf, caption="Konversi PDF berhasil")
        os.remove(img_p)
        os.remove(pdf_p)
        kirim_log(message.from_user, "Foto ke PDF")
    except: bot.reply_to(message, "Gagal memproses gambar.")

@bot.message_handler(func=lambda m: True)
def ai_handler(message):
    bot.send_chat_action(message.chat.id, 'typing')
    bot.reply_to(message, get_ai_response(message.text))
    kirim_log(message.from_user, "Chat AI")

bot.infinity_polling()
