import telebot
from telebot import types
import yt_dlp
import os
import pymongo
from flask import Flask
from threading import Thread
import urllib.parse

# --- الإعدادات (تأكد من وضع ID حسابك) ---
TOKEN = "7954952627:AAEM7OZahtpHnUhUZqM8RBNlYbjUsyOcTng"
# تم استخدام urllib لضمان قراءة كلمة المرور التي تحتوي على رموز بشكل صحيح
password = urllib.parse.quote_plus("10010207966##")
MONGO_URI = f"mongodb+srv://abdalrzagDB:{password}@cluster0.fighoyv.mongodb.net/?retryWrites=true&w=majority"
ADMIN_ID = 5524416062 # تأكد من أن هذا هو الـ ID الصحيح الخاص بك

bot = telebot.TeleBot(TOKEN)

# الاتصال بقاعدة البيانات مع معالجة الأخطاء
try:
    client = pymongo.MongoClient(MONGO_URI)
    db = client["VideoDownloader_Bot"]
    users_col = db["users"]
    groups_col = db["groups"]
except Exception as e:
    print(f"MongoDB Error: {e}")

# --- نظام تسجيل المستخدمين ---
def register_user(message):
    try:
        chat_id = message.chat.id
        if message.chat.type == 'private':
            if not users_col.find_one({"user_id": chat_id}):
                users_col.insert_one({
                    "user_id": chat_id,
                    "name": message.from_user.first_name,
                    "user_name": message.from_user.username
                })
        else:
            if not groups_col.find_one({"group_id": chat_id}):
                groups_col.insert_one({"group_id": chat_id, "title": message.chat.title})
    except:
        pass

# --- أوامر التحكم (Admin) ---
@bot.message_handler(commands=['admin'])
def admin_command(message):
    if message.from_user.id == ADMIN_ID:
        u_count = users_col.count_documents({})
        g_count = groups_col.count_documents({})
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👥 عرض أسماء المستخدمين", callback_data="list_users"))
        
        text = f"📊 لوحة التحكم\n\n👤 عدد المستخدمين: {u_count}\n👥 عدد المجموعات: {g_count}"
        bot.reply_to(message, text, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.reply_to(message, "⚠️ هذا الأمر مخصص للمطور فقط.")

@bot.callback_query_handler(func=lambda call: call.data == "list_users")
def list_users_call(call):
    if call.from_user.id == ADMIN_ID:
        users = users_col.find().limit(15)
        text = "📝 آخر 15 مستخدم:\n"
        for u in users:
            text += f"\n👤 {u.get('name')} | @{u.get('user_name') or 'بدون'}"
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

# --- الأوامر العامة والتحميل ---
@bot.message_handler(commands=['start'])
def start(message):
    register_user(message)
    bot.reply_to(message, "👋 أهلاً بك! أرسل رابط الفيديو للتحميل.")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("http"))
def download_handler(message):
    url = message.text
    # حماية من الروابط الطويلة جداً في الأزرار
    if len(url) > 50: 
        bot.reply_to(message, "⏳ جاري التحميل المباشر (الرابط طويل)...")
        # كود التحميل المباشر هنا...
    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🎥 فيديو", callback_data=f"dl|{url}"))
        bot.reply_to(message, "اختر الصيغة:", reply_markup=markup)

# --- سيرفر ويب للبقاء حياً على Render ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Active ✅"

def run():
    app.run(host='0.0.0.0', port=10000)

if __name__ == "__main__":
    # تشغيل السيرفر في خلفية
    Thread(target=run).start()
    # تشغيل البوت مع تنظيف الـ Webhook القديم
    bot.remove_webhook()
    print("Bot is starting...")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
