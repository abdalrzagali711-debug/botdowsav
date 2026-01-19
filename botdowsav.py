import telebot
from telebot import types
import yt_dlp
import os
import pymongo
from flask import Flask
from threading import Thread
import urllib.parse
import uuid

# --- إعدادات البوت وقاعدة البيانات ---
TOKEN = "7954952627:AAEM7OZahtpHnUhUZqM8RBNlYbjUsyOcTng"
password = "10010207966##"
safe_password = urllib.parse.quote_plus(password)
MONGO_URI = f"mongodb+srv://abdalrzagDB:{safe_password}@cluster0.fighoyv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

ADMIN_ID = 5524416062 

bot = telebot.TeleBot(TOKEN)
client = pymongo.MongoClient(MONGO_URI)
db = client["VideoDownloader_Bot"] 
users_col = db["users"]
links_temp = db["links_temp"] # لتخزين الروابط الطويلة مؤقتاً

app = Flask('')
@app.route('/')
def home(): return "Bot is Active ✅"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, "👋 أرسل رابط فيديو (تيك توك أو إنستقرام) وسأحاول تحميله.")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("http"))
def handle_link(message):
    url = message.text
    # تخزين الرابط في قاعدة البيانات لتجنب خطأ BUTTON_DATA_INVALID
    link_id = str(uuid.uuid4())[:8]
    links_temp.insert_one({"id": link_id, "url": url})

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("📹 فيديو", callback_data=f"vid|{link_id}"),
        types.InlineKeyboardButton("🎵 صوت MP3", callback_data=f"aud|{link_id}")
    )
    bot.reply_to(message, "اختر الصيغة:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: "|" in call.data)
def download_callback(call):
    mode, link_id = call.data.split("|")
    data = links_temp.find_one({"id": link_id})
    if not data:
        bot.answer_callback_query(call.id, "❌ الرابط منتهي الصلاحية، أرسله مجدداً.")
        return
    
    url = data["url"]
    bot.edit_message_text("⏳ جاري المعالجة... قد يستغرق الأمر دقيقة.", call.message.chat.id, call.message.message_id)
    
    ydl_opts = {
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            path = ydl.prepare_filename(info)

            with open(path, 'rb') as f:
                if mode == "vid":
                    bot.send_video(call.message.chat.id, f, caption="✅ تم!")
                else:
                    bot.send_audio(call.message.chat.id, f, caption="✅ تم!")
            
            if os.path.exists(path): os.remove(path)
                
    except Exception as e:
        bot.edit_message_text(f"❌ فشل التحميل. يوتيوب قد يحظر السيرفرات المجانية.", call.message.chat.id, call.message.message_id)

if __name__ == "__main__":
    if not os.path.exists('downloads'): os.makedirs('downloads')
    Thread(target=run_web_server).start()
    # تنظيف الجلسات القديمة عند التشغيل
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)
