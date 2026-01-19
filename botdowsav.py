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

# معالجة كلمة المرور برمجياً لضمان عدم تعطل الرابط
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
    print(f"MongoDB Error: {e}")

# --- سيرفر ويب لـ Render ---
app = Flask('')
@app.route('/')
def home():
    return "Bot is Active ✅"

def run_web_server():
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

# --- الأوامر ---
@bot.message_handler(commands=['start'])
def welcome(message):
    register(message)
    bot.reply_to(message, f"👋 أهلاً بك يا {message.from_user.first_name}!\n\nأرسل لي أي رابط فيديو وسأقوم بتحميله لك فوراً.")

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id == ADMIN_ID:
        u_count = users_col.count_documents({})
        g_count = groups_col.count_documents({})
        bot.reply_to(message, f"📊 إحصائيات قاعدة البيانات:\n👤 مستخدمين: {u_count}\n👥 مجموعات: {g_count}")

# --- معالجة الروابط والتحميل ---
@bot.message_handler(func=lambda m: m.text and m.text.startswith("http"))
def handle_link(message):
    url = message.text
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("📹 فيديو", callback_data=f"vid|{url}"),
        types.InlineKeyboardButton("🎵 صوت MP3", callback_data=f"aud|{url}")
    )
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
            path = ydl.prepare_filename(info)
            if mode == "aud":
                path = path.rsplit('.', 1)[0] + ".mp3"

            with open(path, 'rb') as f:
                if mode == "vid":
                    bot.send_video(call.message.chat.id, f, caption="✅ تم التحميل بنجاح!")
                else:bot.send_audio(call.message.chat.id, f, caption="✅ تم استخراج الصوت!")
            
            if os.path.exists(path):
                os.remove(path)
                
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ فشل التحميل. قد يكون الرابط محظوراً أو الملف كبيراً جداً.", call.message.chat.id, call.message.message_id)

# --- التشغيل ---
if __name__ == "__main__":
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    Thread(target=run_web_server).start()
    bot.infinity_polling(skip_pending=True)
