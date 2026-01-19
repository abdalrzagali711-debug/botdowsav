import telebot
from telebot import types
import yt_dlp
import os
import pymongo
from flask import Flask
from threading import Thread
import urllib.parse

# --- إعدادات البوت وقاعدة البيانات ---
TOKEN = "7954952627:AAEM7OZahtpHnUhUZqM8RBNlYbjUsyOcTng"

# معالجة كلمة المرور التي تحتوي على رموز خاصة برمجياً
password = "10010207966##"
safe_password = urllib.parse.quote_plus(password)
MONGO_URI = f"mongodb+srv://abdalrzagDB:{safe_password}@cluster0.fighoyv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

ADMIN_ID = 5524416062 

bot = telebot.TeleBot(TOKEN)

# الاتصال بـ MongoDB
try:
    client = pymongo.MongoClient(MONGO_URI)
    db = client["VideoDownloader_Bot"] 
    users_col = db["users"]
    groups_col = db["groups"]
except Exception as e:
    print(f"MongoDB Connection Error: {e}")

# --- سيرفر ويب لـ Render ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online ✅"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- نظام تسجيل المستخدمين ---
def register(message):
    chat_id = message.chat.id
    try:
        if message.chat.type == 'private':
            if not users_col.find_one({"user_id": chat_id}):
                users_col.insert_one({
                    "user_id": chat_id, 
                    "first_name": message.from_user.first_name,
                    "username": message.from_user.username
                })
        else:
            if not groups_col.find_one({"group_id": chat_id}):
                groups_col.insert_one({
                    "group_id": chat_id, 
                    "title": message.chat.title
                })
    except:
        pass

# --- لوحة تحكم المطور ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id == ADMIN_ID:
        u_count = users_col.count_documents({})
        g_count = groups_col.count_documents({})
        stats = (f"📊 إحصائيات البوت:\n\n"
                 f"👤 عدد المستخدمين: {u_count}\n"
                 f"👥 عدد المجموعات: {g_count}")
        bot.reply_to(message, stats, parse_mode="Markdown")

# --- القائمة الترحيبية ---
@bot.message_handler(commands=['start'])
def welcome(message):
    register(message)
    welcome_text = f"👋 أهلاً بك يا {message.from_user.first_name}!\n🚀 أرسل رابط الفيديو (إنستقرام، تيك توك، سناب) وسأقوم بتحميله لك."
    bot.send_message(message.chat.id, welcome_text)

# --- معالجة الروابط ---
@bot.message_handler(func=lambda m: m.text and m.text.startswith("http"))
def handle_link(message):
    register(message)
    url = message.text
    if "youtube" in url.lower() or "youtu.be" in url.lower():
        bot.reply_to(message, "⚠️ اليوتيوب غير مدعوم حالياً.")
        return

    markup = types.InlineKeyboardMarkup()
    btn_vid = types.InlineKeyboardButton("📹 فيديو", callback_data=f"vid|{url}")
    btn_aud = types.InlineKeyboardButton("🎵 صوت MP3", callback_data=f"aud|{url}")
    markup.add(btn_vid, btn_aud)
    bot.reply_to(message, "اختر الصيغة المطلوبة:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: "|" in call.data)
def download_callback(call):
    mode, url = call.data.split("|")
    bot.edit_message_text("⏳ جاري التحميل... يرجى الانتظار.", call.message.chat.id, call.message.message_id)
    
    ydl_opts = {
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    if mode == "aud":
        ydl_opts.update({'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}]})
    else:
        ydl_opts['format'] = 'best'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            if mode == "aud":
                file_path = file_path.rsplit('.', 1)[0] + ".mp3"
                with open(file_path, 'rb') as f:
            if mode == "vid":
                bot.send_video(call.message.chat.id, f, caption="✅ تم التحميل بنجاح!")
            else:
                bot.send_audio(call.message.chat.id, f, caption="✅ تم استخراج الصوت!")

        if os.path.exists(file_path):
            os.remove(file_path)
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ فشل التحميل. قد يكون الرابط محظوراً أو حجمه كبيراً.", call.message.chat.id, call.message.message_id)

# --- تشغيل البوت ---
if __name__ == "__main__":
    if not os.path.exists('downloads'): os.makedirs('downloads')
    Thread(target=run).start()
    bot.infinity_polling(skip_pending=True)
