import telebot
from telebot import types
import yt_dlp
import os
import pymongo
from flask import Flask
from threading import Thread
import urllib.parse

# --- الإعدادات (تم ضبطها بناءً على بياناتك) ---
TOKEN = "7954952627:AAEM7OZahtpHnUhUZqM8RBNlYbjUsyOcTng"
# معالجة الباسورد لضمان عمل قاعدة البيانات
safe_pass = urllib.parse.quote_plus("10010207966##")
MONGO_URI = f"mongodb+srv://abdalrzagDB:{safe_pass}@cluster0.fighoyv.mongodb.net/?retryWrites=true&w=majority"
ADMIN_ID = 5524416062  # الـ ID الخاص بك

bot = telebot.TeleBot(TOKEN)

# الاتصال بـ MongoDB
try:
    client = pymongo.MongoClient(MONGO_URI)
    db = client["MediaDownloader"]
    users_col = db["users"]
except Exception as e:
    print(f"DB Error: {e}")

# --- سيرفر الويب للبقاء حياً ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online ✅"

def run(): app.run(host='0.0.0.0', port=10000)

# --- وظائف الآدمن والتحكم ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id == ADMIN_ID:
        count = users_col.count_documents({})
        text = f"📊 إحصائيات البوت:\n\n👤 عدد المستخدمين: {count}\n🚀 الحالة: يعمل بأقصى سرعة"
        bot.reply_to(message, text, parse_mode="Markdown")
    else:
        bot.reply_to(message, "⚠️ مخصص للمطور فقط.")

# --- التحميل والمعالجة ---
@bot.message_handler(commands=['start'])
def start(message):
    # تسجيل المستخدم
    if not users_col.find_one({"user_id": message.chat.id}):
        users_col.insert_one({"user_id": message.chat.id, "name": message.from_user.first_name})
    bot.reply_to(message, "🚀 أرسل رابط الفيديو (TikTok, IG, YT) وسأرسله لك فوراً!")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("http"))
def download_video(message):
    url = message.text
    msg = bot.reply_to(message, "⏳ جاري التحميل والرفع... يرجى الانتظار.")
    
    # إعدادات التحميل السريع والخفيف
    ydl_opts = {
        'format': 'best[ext=mp4]/best', # اختيار أفضل صيغة MP4 متوافقة
        'outtmpl': f'downloads/{message.chat.id}_%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'max_filesize': 45000000, # تحديد 45 ميجا لضمان سرعة الرفع على تليجرام
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
            with open(file_path, 'rb') as video:
                bot.send_video(message.chat.id, video, caption="✅ تم التحميل بواسطة بوتك")
            
            if os.path.exists(file_path): os.remove(file_path) # حذف الملف لتوفير المساحة
            bot.delete_message(message.chat.id, msg.message_id)
            
    except Exception as e:
        bot.edit_message_text(f"❌ فشل التحميل: الملف كبير جداً أو الرابط غير مدعوم.", message.chat.id, msg.message_id)

# --- تشغيل البوت ---
if __name__ == "__main__":
    if not os.path.exists('downloads'): os.makedirs('downloads')
    Thread(target=run).start()
    
    # تنظيف الجلسات القديمة لمنع الـ Conflict
    bot.remove_webhook()
    print("Bot is Live! 🚀")
    bot.infinity_polling(timeout=60, long_polling_timeout=30)
