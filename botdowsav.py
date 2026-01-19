import telebot
from telebot import types
import yt_dlp
import os
import pymongo
from flask import Flask
from threading import Thread

# --- الإعدادات الأساسية ---
# استبدل هذه القيم ببياناتك الحقيقية
TOKEN = "7954952627:AAEM7OZahtpHnUhUZqM8RBN1YbjUsyOcTng" # توكن البوت
MONGO_URI = "mongodb+srv://abdalrzagDB:10010207966##@cluster0.fighoyv.mongodb.net/?retryWrites=true&w=majority" # رابط قاعدة البيانات
ADMIN_ID = 5524416062  # !!! هام: استبدل هذا الرقم بـ ID حسابك الحقيقي !!!

bot = telebot.TeleBot(TOKEN)
client = pymongo.MongoClient(MONGO_URI)
db = client["VideoDownloader_Bot"]
users_col = db["users"]
groups_col = db["groups"]
blacklist_col = db["blacklist"] # لقائمة الحظر

# --- وظائف قاعدة البيانات ---
def add_user(user):
    if not users_col.find_one({"user_id": user.id}):
        users_col.insert_one({
            "user_id": user.id,
            "username": user.username,
            "first_name": user.first_name
        })

def add_group(chat):
    if not groups_col.find_one({"group_id": chat.id}):
        groups_col.insert_one({
            "group_id": chat.id,
            "title": chat.title
        })

# --- لوحة التحكم (Admin Panel) ---
@bot.message_handler(commands=['admin'])
@bot.message_handler(func=lambda m: m.text == "admin")
def admin_panel(message):
    if message.from_user.id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn1 = types.InlineKeyboardButton("📊 الإحصائيات", callback_data="stats")
        btn2 = types.InlineKeyboardButton("🚫 الحظر", callback_data="manage_ban")
        btn3 = types.InlineKeyboardButton("📢 إذاعة", callback_data="broadcast")
        btn4 = types.InlineKeyboardButton("👥 قائمة المستخدمين", callback_data="list_users")
        markup.add(btn1, btn2, btn3, btn4)
        bot.reply_to(message, "🛠 أهلاً بك في لوحة تحكم المطور:", reply_markup=markup, parse_mode="Markdown")
    else:
        bot.reply_to(message, "⚠️ هذا الأمر مخصص للمطور فقط.")

@bot.callback_query_handler(func=lambda call: True)
def admin_callbacks(call):
    if call.data == "stats":
        u_count = users_col.count_documents({})
        g_count = groups_col.count_documents({})
        b_count = blacklist_col.count_documents({})
        text = f"📊 إحصائيات البوت:\n\n👤 المستخدمين: {u_count}\n👥 المجموعات: {g_count}\n🚫 المحظورين: {b_count}"
        bot.answer_callback_query(call.id)
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=call.message.reply_markup, parse_mode="Markdown")

    elif call.data == "list_users":
        users = users_col.find().limit(20) # عرض آخر 20 مستخدم
        text = "📝 قائمة بآخر المستخدمين:\n"
        for u in users:
            text += f"\n- {u.get('first_name')} (@{u.get('username') or 'لا يوجد'})"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

# --- معالج الرسائل الأساسي ---
@bot.message_handler(commands=['start'])
def start(message):
    if blacklist_col.find_one({"user_id": message.from_user.id}):
        return bot.reply_to(message, "🚫 أنت محظور من استخدام البوت.")
    
    if message.chat.type == 'private':
        add_user(message.from_user)
    else:
        add_group(message.chat)
        
    bot.reply_to(message, f"أهلاً بك {message.from_user.first_name} في بوت تحميل الفيديوهات.\nأرسل الرابط للتحميل مباشرة.")

# --- تشغيل سيرفر ويب لـ Render لضمان عدم التوقف ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Running!"

def run(): app.run(host='0.0.0.0', port=10000)

if __name__ == "__main__":
    t = Thread(target=run)
    t.start()
    print("Bot is starting...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
