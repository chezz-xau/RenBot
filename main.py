import os
import threading
from flask import Flask
import telebot
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0")) 

WHITELISTED_USERS = [
    ADMIN_ID,
]

bot = telebot.TeleBot(BOT_TOKEN)

# 1. Pelayan web mini untuk memenuhi syarat Web Service Render (Percuma)
app = Flask(__name__)

@app.route("/")
def home():
    return "RenBot is active and running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# 2. Fungsi Telegram Bot
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    if user_id not in WHITELISTED_USERS:
        bot.reply_to(
            message,
            f"Maaf, {user_name}. Anda belum berdaftar untuk menggunakan bot demo ini.\n\n"
            f"🆔 **Telegram ID anda:** `{user_id}`\n"
            f"Sila hantar ID ini kepada Admin untuk aktifkan akses.",
            parse_mode="Markdown"
        )
        return

    bot.reply_to(
        message, 
        f"Selamat datang, {user_name}! 🏠\n"
        f"Sistem Real Estate Listing aktif.\n\n"
        f"Guna /add untuk mula simpan listing baru."
    )

@bot.message_handler(commands=['add'])
def add_listing(message):
    user_id = message.from_user.id
    if user_id not in WHITELISTED_USERS:
        return
    bot.reply_to(message, "Mod tambah listing diaktifkan. (Seterusnya kita akan bina langkah input data rumah).")

if __name__ == "__main__":
    # Jalankan Flask dalam background thread
    t = threading.Thread(target=run_flask)
    t.start()
    
    print("Bot sedang berjalan...")
    bot.infinity_polling()

