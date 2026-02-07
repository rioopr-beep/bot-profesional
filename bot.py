import telebot
import os
import yt_dlp
import fitz
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

bot = telebot.TeleBot(TOKEN)
client = Groq(api_key=GROQ_API_KEY)

# Server untuk Koyeb agar tidak idle
def run_server():
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", 8000), handler) as httpd:
        httpd.serve_forever()
threading.Thread(target=run_server, daemon=True).start()

# --- FUNGSI INTI ---
def kirim_log(user, aksi):
    try:
        nama = user.first_name or "User"
        uname = f"@{user.username}" if user.username else "N/A"
        pesan = f"🔔 LOG AKTIVITAS\n👤 Nama: {nama}\n🆔 User: {uname}\n🛠 Aksi: {aksi}"
        bot.send_message(ADMIN_ID, pesan)
    except:
        pass

def get_ai_response(prompt):
    try:
        chat_completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": "Anda adalah asisten cerdas yang ringkas dan jelas."},
                {"role": "user", "content": prompt}
            ]
        )
        return chat_completion.choices[0].message.content
    except:
        return "⚠️ Maaf, layanan AI sedang sibuk."

# --- HANDLERS ---

@bot.message_handler(commands=['start', 'help'])
def welcome(message):
    teks = (
        "Selamat Datang di Asisten Kamu\n\n"
        "Fitur yang tersedia:\n"
        "• Chat AI: Langsung ketik pertanyaan\n"
        "• Downloader: Kirim link TikTok/IG/FB/YT\n"
        "• Ringkasan: Kirim link YouTube\n"
        "• Dokumen: Kirim Foto ke PDF / PDF ke Gambar"
    )
    bot.reply_to(message, teks)
    kirim_log(message.from_user, "Membuka Menu Utama")

@bot.message_handler(content_types=['photo', 'document'])
def handle_files(message):
    uid = message.chat.id
    try:
        if message.content_type == 'photo':
            msg = bot.reply_to(message, "⏳ Memproses Foto ke PDF...")
            file_id = message.photo[-1].file_id
            file_info = bot.get_file(file_id)
            downloaded = bot.download_file(file_info.file_path)
            
            img_path, pdf_path = f"img_{uid}.jpg", f"doc_{uid}.pdf"
            with open(img_path, "wb") as f: f.write(downloaded)
            
            Image.open(img_path).convert('RGB').save(pdf_path)
            with open(pdf_path, 'rb') as f:
                bot.send_document(uid, f, caption="✅ PDF Berhasil Dibuat")
            
            os.remove(img_path); os.remove(pdf_path)
            bot.delete_message(uid, msg.message_id)
            kirim_log(message.from_user, "Konversi Foto -> PDF")

        elif message.document.file_name.lower().endswith('.pdf'):
            msg = bot.reply_to(message, "⏳ Mengekstrak PDF ke Gambar...")
            file_info = bot.get_file(message.document.file_id)
            downloaded = bot.download_file(file_info.file_path)
            
            path = f"temp_{uid}.pdf"
            with open(path, "wb") as f: f.write(downloaded)
            
            doc = fitz.open(path)
            for i in range(len(doc)):
                pix = doc.load_page(i).get_pixmap()
                img_name = f"page_{i}_{uid}.jpg"
                pix.save(img_name)
                with open(img_name, 'rb') as f: bot.send_photo(uid, f)
                os.remove(img_name)
            
            doc.close(); os.remove(path)
            bot.delete_message(uid, msg.message_id)
            kirim_log(message.from_user, "Konversi PDF -> Gambar")
    except:
        bot.reply_to(message, "❌ Gagal memproses file.")

@bot.message_handler(func=lambda m: m.text and m.text.startswith('http'))
def handle_links(message):
    url, uid = message.text, message.chat.id
    
    # Mode Ringkasan YT
    if "youtube.com" in url or "youtu.be" in url:
        msg = bot.reply_to(message, "🔍 Menganalisis Video...")
        try:
            vid = url.split("v=")[1].split("&")[0] if "v=" in url else url.split("/")[-1]
            transcript = YouTubeTranscriptApi.get_transcript(vid, languages=['id', 'en'])
            text = " ".join([t['text'] for t in transcript])
            summary = get_ai_response(f"Berikan poin ringkasan dari teks ini: {text[:5000]}")
            bot.edit_message_text(f"📝 RINGKASAN VIDEO:\n\n{summary}", uid, msg.message_id)
            kirim_log(message.from_user, "Ringkasan YouTube")
            return
        except:
            bot.edit_message_text("⚠️ Gagal mengambil transkrip. Mencoba download...", uid, msg.message_id)
    else:
        msg = bot.reply_to(message, "📥 Sedang Mengunduh...")

    # Mode Download
    try:
        opts = {'format': 'best[height<=720]', 'outtmpl': f"vid_{uid}.%(ext)s", 'quiet': True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            fname = ydl.prepare_filename(info)
            with open(fname, 'rb') as f:
                bot.send_video(uid, f, caption="✅ Berhasil Diunduh")
            os.remove(fname)
            kirim_log(message.from_user, f"Download: {info.get('extractor_key')}")
        bot.delete_message(uid, msg.message_id)
    except:
        bot.edit_message_text("❌ Gagal mengunduh media.", uid, msg.message_id)

@bot.message_handler(func=lambda m: True)
def handle_ai(message):
    bot.send_chat_action(message.chat.id, 'typing')
    response = get_ai_response(message.text)
    bot.reply_to(message, response)
    kirim_log(message.from_user, f"AI: {message.text[:20]}...")

# Run
bot.infinity_polling(timeout=20, long_polling_timeout=10)
