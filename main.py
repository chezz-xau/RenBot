import os
import telebot
from telebot import types
import psycopg2
from psycopg2.extras import RealDictCursor
import threading
from flask import Flask

# ================= CONFIGURATION =================
TOKEN = os.environ.get('BOT_TOKEN')
DATABASE_URL = os.environ.get('DATABASE_URL')

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "RenBot is alive and running!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# ================= DATABASE SETUP =================
def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS listings (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            trans_type TEXT,
            property_type TEXT,
            title TEXT,
            location TEXT,
            price TEXT,
            bedrooms TEXT,
            bathrooms TEXT,
            parking TEXT,
            size TEXT,
            tenure TEXT,
            features TEXT,
            contact TEXT,
            remarks TEXT,
            photo_id TEXT
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

init_db()

# ================= BOT COMMANDS =================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    bot.clear_step_handler_by_chat_id(message.chat.id)
    
    bot.reply_to(
        message, 
        f"Selamat datang, **{user_name}**! 🏠\n"
        f"Sistem *RenBot Real Estate Listing* (Mod Percubaan Demo).\n\n"
        f"• Guna /add untuk tambah listing baharu.\n"
        f"• Guna /list untuk lihat senarai listing anda.\n\n"
        f"🆔 **ID Telegram Anda:** `{user_id}`",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['list'])
def list_listings(message):
    user_id = message.from_user.id
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM listings WHERE user_id = %s ORDER BY id DESC", (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        bot.reply_to(message, "📂 Tiada listing hartanah yang tersimpan lagi.")
        return

    bot.reply_to(message, f"📋 **SENARAI HARTANAH ANDA ({len(rows)}):**", parse_mode="Markdown")
    
    for row in rows:
        markup = types.InlineKeyboardMarkup()
        btn_view = types.InlineKeyboardButton("👁️ Lihat Detail", callback_data=f"view_{row['id']}")
        btn_del = types.InlineKeyboardButton("🗑️ Padam", callback_data=f"del_{row['id']}")
        markup.add(btn_view, btn_del)

        text = f"🏢 **ID #{row['id']} - {row['property_type']}**\n📍 Lokasi: {row['location']}\n💰 Harga: RM {row['price']}"
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

# ================= ADD LISTING FLOW (15 STEPS) =================
@bot.message_handler(commands=['add'])
def add_start(message):
    user_id = message.from_user.id
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add("WTS (For Sale)", "WTL (For Rent)")
    msg = bot.reply_to(message, "📌 **Langkah 1/15:** Pilih jenis urus niaga:", reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_trans_type)

def process_trans_type(message):
    data = {'user_id': message.from_user.id, 'trans_type': message.text}
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add("Condo", "Serviced Residence", "Apartment", "Terraced House", "Semi-D", "Bungalow", "Land", "Commercial")
    msg = bot.reply_to(message, "📌 **Langkah 2/15:** Pilih Jenis Hartanah:", reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_property_type, data)

def process_property_type(message, data):
    data['property_type'] = message.text
    msg = bot.reply_to(message, "📌 **Langkah 3/15:** Sila masukkan **Tajuk Iklan / Headline**:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_title, data)

def process_title(message, data):
    data['title'] = message.text
    msg = bot.reply_to(message, "📌 **Langkah 4/15:** Sila masukkan **Lokasi / Kawasan** (Cth: Mont Kiara, KL):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_location, data)

def process_location(message, data):
    data['location'] = message.text
    msg = bot.reply_to(message, "📌 **Langkah 5/15:** Sila masukkan **Harga (RM)** (Cth: 550000):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_price, data)

def process_price(message, data):
    data['price'] = message.text
    msg = bot.reply_to(message, "📌 **Langkah 6/15:** Bilangan Bilik Tidur (Cth: 3):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_bedrooms, data)

def process_bedrooms(message, data):
    data['bedrooms'] = message.text
    msg = bot.reply_to(message, "📌 **Langkah 7/15:** Bilangan Bilik Air (Cth: 2):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_bathrooms, data)

def process_bathrooms(message, data):
    data['bathrooms'] = message.text
    msg = bot.reply_to(message, "📌 **Langkah 8/15:** Jumlah Petak Parkir (Cth: 1):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_parking, data)

def process_parking(message, data):
    data['parking'] = message.text
    msg = bot.reply_to(message, "📌 **Langkah 9/15:** Keluasan (Build-up / Land Area dalam sqft) (Cth: 1050 sqft):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_size, data)

def process_size(message, data):
    data['size'] = message.text
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add("Freehold", "Leasehold", "Malay Reserve", "Bumi Lot", "Non-Bumi Lot")
    msg = bot.reply_to(message, "📌 **Langkah 10/15:** Status Pegangan (Tenure):", reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_tenure, data)

def process_tenure(message, data):
    data['tenure'] = message.text
    msg = bot.reply_to(message, "📌 **Langkah 11/15:** Keistimewaan / Renovation (Cth: Fully Furnished, Kitchen Cabinet):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_features, data)

def process_features(message, data):
    data['features'] = message.text
    msg = bot.reply_to(message, "📌 **Langkah 12/15:** Nombor Telefon / Link WhatsApp Untuk Dihubungi:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_contact, data)

def process_contact(message, data):
    data['contact'] = message.text
    msg = bot.reply_to(message, "📌 **Langkah 13/15:** Nota Tambahan / Remarks (Atau taip 'Tiada'):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_remarks, data)

def process_remarks(message, data):
    data['remarks'] = message.text
    markup = types.ForceReply(selective=True)
    msg = bot.reply_to(message, "📌 **Langkah 14/15:** Sila muat naik **1 keping gambar hartanah**:", reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_photo, data)

def process_photo(message, data):
    if not message.photo:
        msg = bot.reply_to(message, "⚠️ Sila hantar **gambar** hartanah (bukan dokumen/teks). Cuba hantar semula:")
        bot.register_next_step_handler(msg, process_photo, data)
        return

    data['photo_id'] = message.photo[-1].file_id

    summary = (
        f"📋 **SEMAKAN MAKLUMAT LISTING**\n\n"
        f"🔹 **Jenis:** {data['trans_type']} - {data['property_type']}\n"
        f"🏷️ **Tajuk:** {data['title']}\n"
        f"📍 **Lokasi:** {data['location']}\n"
        f"💰 **Harga:** RM {data['price']}\n"
        f"🛏️ **Bilik:** {data['bedrooms']} | 🚿 **Air:** {data['bathrooms']} | 🚗 **Parkir:** {data['parking']}\n"
        f"📐 **Keluasan:** {data['size']}\n"
        f"📜 **Tenure:** {data['tenure']}\n"
        f"✨ **Ciri:** {data['features']}\n"
        f"📞 **Kontak:** {data['contact']}\n"
        f"📝 **Remarks:** {data['remarks']}\n\n"
        f"Adakah anda ingin simpan listing ini?"
    )
    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add("💾 Simpan Listing", "❌ Batalkan")
    msg = bot.reply_to(message, summary, reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(msg, save_listing_to_db, data)

def save_listing_to_db(message, data):
    if message.text != "💾 Simpan Listing":
        bot.reply_to(message, "❌ Proses penambahan listing dibatalkan.", reply_markup=types.ReplyKeyboardRemove())
        return

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO listings (user_id, trans_type, property_type, title, location, price, bedrooms, bathrooms, parking, size, tenure, features, contact, remarks, photo_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (
        data['user_id'], data['trans_type'], data['property_type'], data['title'],
        data['location'], data['price'], data['bedrooms'], data['bathrooms'],
        data['parking'], data['size'], data['tenure'], data['features'],
        data['contact'], data['remarks'], data['photo_id']
    ))
    conn.commit()
    cur.close()
    conn.close()

    bot.reply_to(message, "✅ **Berjaya!** Listing hartanah anda telah disimpan secara kekal di awan.", reply_markup=types.ReplyKeyboardRemove(), parse_mode="Markdown")

# ================= CALLBACK HANDLER (VIEW & DELETE) =================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    parts = call.data.split('_')
    action = parts[0]
    listing_id = parts[1]

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM listings WHERE id = %s", (listing_id,))
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        bot.answer_callback_query(call.id, "❌ Rekod tidak dijumpai.")
        return

    if action == "view":
        caption = (
            f"🏠 **{row['property_type']} ({row['trans_type']})**\n\n"
            f"🏷️ **{row['title']}**\n"
            f"📍 **Lokasi:** {row['location']}\n"
            f"💰 **Harga:** RM {row['price']}\n"
            f"🛏️ **Bilik:** {row['bedrooms']} | 🚿 **Air:** {row['bathrooms']} | 🚗 **Parkir:** {row['parking']}\n"
            f"📐 **Saiz:** {row['size']}\n"
            f"📜 **Tenure:** {row['tenure']}\n"
            f"✨ **Ciri:** {row['features']}\n"
            f"📞 **Hubungi:** {row['contact']}\n"
            f"📝 **Nota:** {row['remarks']}"
        )
        if row['photo_id']:
            bot.send_photo(call.message.chat.id, row['photo_id'], caption=caption, parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, caption, parse_mode="Markdown")
        bot.answer_callback_query(call.id)

    elif action == "del":
        cur.execute("DELETE FROM listings WHERE id = %s", (listing_id,))
        conn.commit()
        bot.answer_callback_query(call.id, "🗑️ Listing berjaya dipadam!")
        bot.edit_message_text("🗑️ *Listing ini telah dipadam.*", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

    cur.close()
    conn.close()

# ================= MAIN EXECUTION =================
if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.start()
    
    # Menghapuskan sebarang konflik webhook/sesi lama
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)
