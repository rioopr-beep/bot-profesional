import telebot
import os
import yt_dlp
import fitz  # PyMuPDF
import time
import threading
import http.server
import socketserver
from groq import Groq
from PIL import Image

# --- KONFIGURASI (Ganti dengan Token/Key Anda) ---
TOKEN = '8411809165:AAEY_6CfQwAVO4zag2S-iwiKFluG9R8Ky8Y'
GROQ_KEY = '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'

# Inisialisasi Bot & AI
bot = telebot.TeleBot(TOKEN, threaded=False)
client = Groq(api_key=GROQ_KEY)

# --- SERVER DUMMY (Agar Koyeb tetap Healthy) ---
def run_server():
    try:
        handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", 8000), handler) as httpd:
            httpd.serve_forever()
    except: pass
threading.Thread(target=run_server, daemon=True).start()

# --- FUNGSI PEMBANTU ---
def get_ai_response(prompt):
    try:
        chat = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}]
        )
        return chat.choices[0].message.content
    except Exception as e:
        return f"⚠️ Groq AI Error: {str(e)[:50]}"

# --- HANDLER COMMANDS ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 **Halo! Saya Bot Serbaguna.**\n\n"
        "**Apa yang bisa saya lakukan?**\n"
        "💬 **Chat AI**: Langsung kirim pesan teks saja.\n"
        "🎥 **YouTube**: Kirim link video untuk dapat link download.\n"
        "📄 **PDF**: Kirim file PDF untuk diringkas otomatis.\n"
        "📸 **Foto**: Kirim foto (Fitur edit segera hadir)."
    )
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

# --- HANDLER YOUTUBE ---
@bot.message_handler(regexp=r'(https?://)?(www\.)?(youtube|youtu|be)\.(com|be)/')
def handle_youtube(message):
    url = message.text
    msg = bot.reply_to(message, "⏳ Sedang memproses link YouTube...")
    
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'add_header': ['User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36']
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Video')
            # Ambil URL kualitas terbaik yang tersedia
            download_url = info.get('url') if not info.get('formats') else info['formats'][-1].get('url')
            
            bot.edit_message_text(
                f"🎥 **Judul:** {title}\n\n✅ **Link Berhasil Diambil!**\n[Klik di sini untuk Download]({download_url})",
                message.chat.id, msg.message_id, parse_mode='Markdown'
            )
    except Exception as e:
        error_str = str(e)
        if "Sign in" in error_str:
            bot.edit_message_text("❌ YouTube memblokir akses server (Bot Detection). Coba video lain.", message.chat.id, msg.message_id)
        else:
            bot.edit_message_text(f"❌ Error: {error_str[:100]}", message.chat.id, msg.message_id)

# --- HANDLER DOKUMEN (PDF) ---
@bot.message_handler(content_types=['document'])
def handle_docs(message):
    if message.document.mime_type == 'application/pdf':
        msg = bot.reply_to(message, "📄 Sedang membaca dan meringkas PDF...")
        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            with open("temp.pdf", "wb") as f:
                f.write(downloaded_file)
            
            doc = fitz.open("temp.pdf")
            full_text = ""
            for i in range(min(5, len(doc))): # Ambil teks dari maksimal 5 halaman pertama
                full_text += doc[i].get_text()
            doc.close()

            summary = get_ai_response(f"Ringkas teks berikut secara singkat dan padat dalam bahasa Indonesia: {full_text[:3000]}")
            bot.edit_message_text(f"📝 **Ringkasan PDF:**\n\n{summary}", message.chat.id, msg.message_id)
            
            if os.path.exists("temp.pdf"): os.remove("temp.pdf")
        except Exception as e:
            bot.edit_message_text(f"❌ Gagal memproses PDF: {str(e)[:50]}", message.chat.id, msg.message_id)

# --- HANDLER FOTO ---
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.reply_to(message, "📸 Foto diterima! Saat ini saya hanya bisa menerima foto, fitur editing akan segera ditambahkan.")

# --- HANDLER CHAT AI (DEFAULT) ---
@bot.message_handler(func=lambda m: True)
def handle_chat(message):
    bot.send_chat_action(message.chat.id, 'typing')
    response = get_ai_response(message.text)
    bot.reply_to(message, response)

# --- STARTUP ---
if __name__ == "__main__":
    print("Bot is starting...")
    while True:
        try:
            bot.remove_webhook()
            # Interval 2 detik untuk menghindari 'Conflict 409'
            bot.polling(none_stop=True, interval=2, timeout=20)
        except Exception as e:
            print(f"Polling Error: {e}")
            time.sleep(5)
    time.sleep(1)
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=20)
        except:
            time.sleep(5)
