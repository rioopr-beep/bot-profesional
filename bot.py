import telebot
import os
import yt_dlp
import fitz  # PyMuPDF
import time
import threading
import http.server
import socketserver
from groq import Groq
from youtube_transcript_api import YouTubeTranscriptApi

# --- KONFIGURASI BARU ---
TOKEN = '8411809165:AAFDDtik7z7dWEanPsPESEDFuNRwqcfVc48'
GROQ_KEY = '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'

bot = telebot.TeleBot(TOKEN, threaded=False)
client = Groq(api_key=GROQ_KEY)

# Server Dummy agar Koyeb tetap Healthy
def run_server():
    try:
        handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", 8000), handler) as httpd:
            httpd.serve_forever()
    except: pass
threading.Thread(target=run_server, daemon=True).start()

# --- FUNGSI AI ---
def get_ai_response(prompt):
    try:
        chat = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}]
        )
        return chat.choices[0].message.content
    except Exception as e:
        return f"⚠️ Groq AI Error: {str(e)[:50]}"

# --- FUNGSI YOUTUBE SUMMARIZER ---
def get_youtube_summary(video_id):
    try:
        # Mencoba ambil subtitle (Indo lalu Inggris)
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['id', 'en'])
        text = " ".join([t['text'] for t in transcript_list])
        summary = get_ai_response(f"Ringkas poin utama video ini dalam Bahasa Indonesia: {text[:4000]}")
        return summary
    except:
        return "❌ Subtitle tidak ditemukan. Ringkasan tidak bisa dibuat."

# --- HANDLER COMMANDS ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "🤖 **Bot Aktif dengan Token Baru!**\n\nKirim link YouTube untuk download & ringkasan, atau PDF untuk diringkas.", parse_mode='Markdown')

# --- HANDLER YOUTUBE ---
@bot.message_handler(regexp=r'(https?://)?(www\.)?(youtube|youtu|be)\.(com|be)/')
def handle_youtube(message):
    url = message.text
    msg = bot.reply_to(message, "⏳ Memproses YouTube...")
    
    video_id = None
    if "v=" in url: video_id = url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in url: video_id = url.split("youtu.be/")[1].split("?")[0]

    ydl_opts = {'format': 'best', 'quiet': True, 'nocheckcertificate': True}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Video')
            dl_url = info.get('url') if not info.get('formats') else info['formats'][-1].get('url')
        
        summary = get_youtube_summary(video_id) if video_id else "ID tidak valid."
        
        bot.edit_message_text(f"🎥 **{title}**\n\n📝 **Ringkasan:**\n{summary}\n\n✅ [Download Video]({dl_url})", 
                             message.chat.id, msg.message_id, parse_mode='Markdown')
    except Exception as e:
        bot.edit_message_text(f"❌ Error: {str(e)[:50]}", message.chat.id, msg.message_id)

# --- HANDLER PDF ---
@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    if message.document.mime_type == 'application/pdf':
        msg = bot.reply_to(message, "📄 Membaca PDF...")
        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded = bot.download_file(file_info.file_path)
            with open("temp.pdf", "wb") as f: f.write(downloaded)
            
            doc = fitz.open("temp.pdf")
            text = "".join([page.get_text() for page in doc[:3]])
            doc.close()
            
            summary = get_ai_response(f"Ringkas teks ini: {text[:3000]}")
            bot.reply_to(message, f"📝 **Ringkasan PDF:**\n\n{summary}")
            os.remove("temp.pdf")
        except:
            bot.reply_to(message, "❌ Gagal meringkas PDF.")

# --- HANDLER CHAT AI ---
@bot.message_handler(func=lambda m: True)
def handle_chat(message):
    bot.reply_to(message, get_ai_response(message.text))

# --- LOOPING AMAN ---
if __name__ == "__main__":
    print("🚀 Bot starting with NEW TOKEN...")
    while True:
        try:
            bot.remove_webhook()
            bot.polling(none_stop=True, interval=2, timeout=20)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)
