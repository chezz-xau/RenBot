import os
import sqlite3
import threading
from flask import Flask
import telebot
from telebot import types
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

WHITELISTED_USERS = [ADMIN_ID]

bot = telebot.TeleBot(BOT_TOKEN)

# ------------------------------------
# 1. DATABASE SETUP (SQLite)
# ------------------------------------
def init_db():
    conn = sqlite3.connect('renbot.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            listing_type TEXT,
            prop_type TEXT,
            tenure TEXT,
            lease_years TEXT,
            lot_status TEXT,
            parking TEXT,
            gated TEXT,
            location TEXT,
            price TEXT,
            market_value TEXT,
            size TEXT,
            rooms TEXT,
            maintenance TEXT,
            surrounding TEXT,
            image_id TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ------------------------------------
# 2. FLASK WEB SERVER (Render Keep-Alive)
# ------------------------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "RenBot Web Service is running with Database!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# Memori Sementara untuk Borang
user_data = {}

# ------------------------------------
# 3. BOT HANDLERS & NAVIGATION
# ------------------------------------

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    if user_id not in WHITELISTED_USERS:
        bot.reply_to(
            message,
            f"Maaf, {user_name}. Anda belum berdaftar.\n\n"
            f"🆔 **ID Telegram Anda:** `{user_id}`\n"
            f"Sila hantar ID ini kepada Admin.",
            parse_mode="Markdown"
        )
        return

    bot.reply_to(
        message, 
        f"Selamat datang, **{user_name}**! 🏠\n"
        f"Sistem *RenBot Real Estate Listing* aktif dengan Database.\n\n"
        f"Gunakan arahan /add untuk mula memasukkan listing baharu\n"
        f"atau /list untuk melihat senarai listing.",
        parse_mode="Markdown"
    )

# --- SENARAIKAN LISTING (/list) ---
@bot.message_handler(commands=['list'])
def list_listings(message):
    user_id = message.from_user.id
    if user_id not in WHITELISTED_USERS:
        return

    conn = sqlite3.connect('renbot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, listing_type, prop_type, location, price FROM listings WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        bot.reply_to(message, "📂 Tiada listing hartanah yang tersimpan dalam sistem lagi.")
        return

    response = "📂 **SENARAI LISTING HARTANAHS ANDA:**\n\n"
    for row in rows:
        response += f"🔹 **ID #{row[0]}** | `{row[1]}` - {row[2]}\n📍 Lokasi: {row[3]}\n💰 Harga: RM {row[4]}\n\n"
    
    bot.reply_to(message, response, parse_mode="Markdown")

# --- MULA PROSES TAMBAH LISTING (/add) ---
@bot.message_handler(commands=['add'])
def start_add_listing(message):
    user_id = message.from_user.id
    if user_id not in WHITELISTED_USERS:
        return

    user_data[user_id] = {}

    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("WTS (For Sale)", callback_data="listing_type_WTS")
    btn2 = types.InlineKeyboardButton("WTL (For Rent)", callback_data="listing_type_WTL")
    markup.add(btn1, btn2)

    bot.send_message(message.chat.id, "📌 **Langkah 1/15:** Pilih jenis urus niaga:", reply_markup=markup, parse_mode="Markdown")

# --- CALLBACK HANDLER FOR BUTTONS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if user_id not in WHITELISTED_USERS:
        return

    data = call.data

    # Simpan Akhir
    if data == "save_listing_final":
        d = user_data.get(user_id, {})
        if not d:
            bot.answer_callback_query(call.id, "Sesi tamat atau data kosong. Sila guna /add semula.")
            return

        conn = sqlite3.connect('renbot.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO listings (user_id, listing_type, prop_type, tenure, lease_years, lot_status, parking, gated, location, price, market_value, size, rooms, maintenance, surrounding, image_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, d.get('listing_type'), d.get('prop_type'), d.get('tenure'), d.get('lease_years'),
            d.get('lot_status'), d.get('parking'), d.get('gated'), d.get('location'),
            d.get('price'), d.get('market_value'), d.get('size'), d.get('rooms'),
            d.get('maintenance'), d.get('surrounding'), d.get('image_id')
        ))
        conn.commit()
        conn.close()

        bot.edit_message_caption("✅ **Berjaya!** Listing hartanah anda telah disimpan secara kekal dalam database.", chat_id, call.message.message_id, parse_mode="Markdown")
        bot.send_message(chat_id, "Guna arahan /list untuk melihat semua senarai listing anda.")
        user_data.pop(user_id, None)
        return

    # Step 1: WTS / WTL
    if data.startswith("listing_type_"):
        user_data[user_id]['listing_type'] = data.split("_")[2]
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("Apartment/Condo", callback_data="prop_type_Apartment/Condo"),
            types.InlineKeyboardButton("Single Storey", callback_data="prop_type_Single Storey"),
            types.InlineKeyboardButton("Double Storey", callback_data="prop_type_Double Storey"),
            types.InlineKeyboardButton("Lain-lain", callback_data="prop_type_Lain-lain")
        )
        bot.edit_message_text("🏠 **Langkah 2/15:** Pilih jenis hartanah:", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    # Step 2: Property Type
    elif data.startswith("prop_type_"):
        user_data[user_id]['prop_type'] = data.replace("prop_type_", "")
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("Freehold", callback_data="tenure_Freehold"),
            types.InlineKeyboardButton("Leasehold", callback_data="tenure_Leasehold")
        )
        bot.edit_message_text("📜 **Langkah 3/15:** Pilih status pegangan tanah (Tenure):", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    # Step 3: Tenure
    elif data.startswith("tenure_"):
        tenure = data.split("_")[1]
        user_data[user_id]['tenure'] = tenure

        if tenure == "Leasehold":
            msg = bot.send_message(chat_id, "⏳ Berapa baki tahun untuk Leasehold ini? (Contoh: `85`):", parse_mode="Markdown")
            bot.register_next_step_handler(msg, ask_lot_status_after_lease)
        else:
            user_data[user_id]['lease_years'] = "N/A"
            ask_lot_status(chat_id)

    # Step 4: Lot Status
    elif data.startswith("lot_"):
        user_data[user_id]['lot_status'] = data.replace("lot_", "")
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("1 Carpark", callback_data="parking_1 Carpark"),
            types.InlineKeyboardButton("2 Carparks", callback_data="parking_2 Carparks"),
            types.InlineKeyboardButton("Lain-lain / Tiada", callback_data="parking_Lain-lain")
        )
        bot.edit_message_text("🚗 **Langkah 5/15:** Pilih bilangan parkir:", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    # Step 5: Parking
    elif data.startswith("parking_"):
        user_data[user_id]['parking'] = data.replace("parking_", "")
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("Ya (Gated & Guarded)", callback_data="gated_Ya"),
            types.InlineKeyboardButton("Tidak", callback_data="gated_Tidak")
        )
        bot.edit_message_text("🛡️ **Langkah 6/15:** Adakah kawasan Gated & Guarded?", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    # Step 6: Gated & Guarded
    elif data.startswith("gated_"):
        user_data[user_id]['gated'] = data.replace("gated_", "")
        
        msg = bot.send_message(chat_id, "📍 **Langkah 7/15:** Masukkan Lokasi / Kawasan Hartanah:\n*(Contoh: Seksyen 13, Shah Alam)*", parse_mode="Markdown")
        bot.register_next_step_handler(msg, step_price)

# --- NEXT STEP TEXT HANDLERS ---

def ask_lot_status_after_lease(message):
    user_id = message.from_user.id
    user_data[user_id]['lease_years'] = message.text
    ask_lot_status(message.chat.id)

def ask_lot_status(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Bumi Lot", callback_data="lot_Bumi Lot"),
        types.InlineKeyboardButton("Malay Reserved", callback_data="lot_Malay Reserved"),
        types.InlineKeyboardButton("Non Bumi Lot", callback_data="lot_Non Bumi Lot")
    )
    bot.send_message(chat_id, "🏷️ **Langkah 4/15:** Pilih status lot:", reply_markup=markup, parse_mode="Markdown")

def step_price(message):
    user_id = message.from_user.id
    user_data[user_id]['location'] = message.text
    msg = bot.send_message(message.chat.id, "💰 **Langkah 8/15:** Masukkan Harga Jualan/Sewa (RM):\n*(Contoh: 450000)*", parse_mode="Markdown")
    bot.register_next_step_handler(msg, step_mv)

def step_mv(message):
    user_id = message.from_user.id
    user_data[user_id]['price'] = message.text
    msg = bot.send_message(message.chat.id, "📊 **Langkah 9/15:** Masukkan Market Value (RM):\n*(Jika tiada, taip 'N/A')*", parse_mode="Markdown")
    bot.register_next_step_handler(msg, step_size)

def step_size(message):
    user_id = message.from_user.id
    user_data[user_id]['market_value'] = message.text
    msg = bot.send_message(message.chat.id, "📐 **Langkah 10/15:** Masukkan Saiz Hartanah:\n*(Contoh: 1,050 sqft)*", parse_mode="Markdown")
    bot.register_next_step_handler(msg, step_rooms)

def step_rooms(message):
    user_id = message.from_user.id
    user_data[user_id]['size'] = message.text
    msg = bot.send_message(message.chat.id, "🛏️ **Langkah 11/15:** Masukkan bilangan Bilik Tidur & Bilik Air:\n*(Contoh: 3 Bilik, 2 Bilik Air)*", parse_mode="Markdown")
    bot.register_next_step_handler(msg, step_maintenance)

def step_maintenance(message):
    user_id = message.from_user.id
    user_data[user_id]['rooms'] = message.text
    msg = bot.send_message(message.chat.id, "💵 **Langkah 12/15:** Masukkan yuran Maintenance (RM):\n*(Jika tiada/bebas, taip 'Tiada')*", parse_mode="Markdown")
    bot.register_next_step_handler(msg, step_surrounding)

def step_surrounding(message):
    user_id = message.from_user.id
    user_data[user_id]['maintenance'] = message.text
    msg = bot.send_message(message.chat.id, "🏙️ **Langkah 13/15:** Masukkan Surrounding Area / Kemudahan Berdekatan:\n*(Contoh: Near LRT, Aeon Mall, Highway Federal)*", parse_mode="Markdown")
    bot.register_next_step_handler(msg, step_image)

def step_image(message):
    user_id = message.from_user.id
    user_data[user_id]['surrounding'] = message.text
    msg = bot.send_message(message.chat.id, "🖼️ **Langkah 14/15:** Hantar satu Gambar Utama Hartanah:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, step_confirm)

def step_confirm(message):
    user_id = message.from_user.id
    
    if message.content_type == 'photo':
        user_data[user_id]['image_id'] = message.photo[-1].file_id
    else:
        user_data[user_id]['image_id'] = None

    d = user_data[user_id]
    
    summary = (
        f"🏠 **SUMMARY LISTING HARTANAH** 🏠\n\n"
        f"📌 **Status:** {d.get('listing_type')} | {d.get('prop_type')}\n"
        f"📍 **Lokasi:** {d.get('location')}\n"
        f"💰 **Harga:** RM {d.get('price')}\n"
        f"📊 **Market Value:** {d.get('market_value')}\n\n"
        f"📐 **Saiz:** {d.get('size')}\n"
        f"🛏️ **Bilik/Bilik Air:** {d.get('rooms')}\n"
        f"📜 **Tenure:** {d.get('tenure')} (Baki: {d.get('lease_years')})\n"
        f"🏷️ **Lot Status:** {d.get('lot_status')}\n"
        f"🛡️ **Gated & Guarded:** {d.get('gated')}\n"
        f"🚗 **Parkir:** {d.get('parking')}\n"
        f"💵 **Maintenance:** {d.get('maintenance')}\n"
        f"🏙️ **Surrounding Area:** {d.get('surrounding')}\n\n"
        f"✅ *Adakah anda mahu menyimpannya ke Database?*"
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💾 Simpan Listing", callback_data="save_listing_final"))

    if d['image_id']:
        bot.send_photo(message.chat.id, d['image_id'], caption=summary, parse_mode="Markdown", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, summary, parse_mode="Markdown", reply_markup=markup)

# ------------------------------------
# MAIN ENTRY POINT
# ------------------------------------
if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.start()
    
    print("RenBot dengan Database sedang berjalan...")
    bot.infinity_polling()
