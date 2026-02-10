import logging
import sqlite3
import hashlib
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.constants import ParseMode

# ============= YOUR DETAILS =============
BOT_TOKEN = "8535390425:AAH4RF9v6k8H6fMQeXr_OQ6JuB7PV8gvgLs"
ADMIN_ID = 7291034213
TELEGRAM_GROUP_LINK = "https://t.me/+P8gZuIBH75RiOThk"
WHATSAPP_GROUP_LINK = "https://chat.whatsapp.com/YOUR_WHATSAPP_LINK"

BINANCE_EMAIL = "techmasterfreelancer@gmail.com"
BINANCE_ID = "1129541950"
BINANCE_NETWORK = "TRC20"

EASYPAYSA_NAME = "Jaffar Ali"
EASYPAYSA_NUMBER = "03486623402"
MEMBERSHIP_FEE = "$5 USD (Lifetime)"
# ========================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "bot.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        email TEXT,
        whatsapp TEXT,
        request_type TEXT,
        proof_file_id TEXT,
        current_step TEXT DEFAULT 'start',
        payment_method TEXT,
        payment_file_id TEXT,
        payment_hash TEXT UNIQUE,
        status TEXT DEFAULT 'new',
        admin_approved INTEGER DEFAULT 0,
        created_at TIMESTAMP,
        updated_at TIMESTAMP
    )''')
    conn.commit()
    conn.close()

init_db()

def get_db():
    return sqlite3.connect(DB_PATH)

def get_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    data = c.fetchone()
    conn.close()
    return data

def create_user(user_id, username):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, created_at, updated_at) VALUES (?, ?, ?, ?)",
              (user_id, username, datetime.now(), datetime.now()))
    conn.commit()
    conn.close()

def update_user(user_id, field, value):
    conn = get_db()
    c = conn.cursor()
    c.execute(f"UPDATE users SET {field}=?, updated_at=? WHERE user_id=?",
              (value, datetime.now(), user_id))
    conn.commit()
    conn.close()

# ================= START =================

async def start(update: Update, context):
    user = update.effective_user
    user_id = user.id

    if not get_user(user_id):
        create_user(user_id, user.username or "NoUsername")

    keyboard = [
        [InlineKeyboardButton("💎 Premium Subscription", callback_data="type_premium")],
        [InlineKeyboardButton("🛒 Product Purchase", callback_data="type_product")]
    ]

    await update.message.reply_text(
        "🎉 Welcome!\n\nSelect what you purchased:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= CALLBACK =================

async def handle_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data.startswith("type_"):
        t = "Premium Subscription" if "premium" in query.data else "Product Purchase"
        update_user(user_id, "request_type", t)
        update_user(user_id, "current_step", "name_pending")
        await query.edit_message_text("📝 Enter your FULL NAME:")
        return

    if query.data.startswith("approve_"):
        target = int(query.data.split("_")[1])
        update_user(target, "admin_approved", 1)
        update_user(target, "status", "payment_pending")

        await context.bot.send_message(
            chat_id=target,
            text=f"🎉 Approved!\n\nPlease pay {MEMBERSHIP_FEE}"
        )

        await query.edit_message_text("✅ Approved & user notified.")
        return

# ================= TEXT =================

async def handle_text(update: Update, context):
    user_id = update.effective_user.id
    text = update.message.text
    user_data = get_user(user_id)

    if not user_data:
        return

    step = user_data[7]

    if step == "name_pending":
        update_user(user_id, "full_name", text)
        update_user(user_id, "current_step", "email_pending")
        await update.message.reply_text("📧 Enter your EMAIL:")
        return

    if step == "email_pending":
        update_user(user_id, "email", text)
        update_user(user_id, "current_step", "whatsapp_pending")
        await update.message.reply_text("📱 Enter your WhatsApp (+92300XXXXXXX):")
        return

    # 🔥 FIXED ADMIN NOTIFICATION PART
    if step == "whatsapp_pending":
        update_user(user_id, "whatsapp", text)
        update_user(user_id, "current_step", "info_submitted")

        # 🔥 GET FRESH DATA AFTER UPDATE
        updated_user = get_user(user_id)

        await update.message.reply_text("✅ Submitted! Waiting for admin review.")

        keyboard = [
            [
                InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{user_id}"),
                InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{user_id}")
            ]
        ]

        admin_message = f"""
🚨 NEW APPLICATION

👤 Username: @{updated_user[1]}
🆔 User ID: {user_id}
📌 Type: {updated_user[5]}

📝 Name: {updated_user[2]}
📧 Email: {updated_user[3]}
📱 WhatsApp: {updated_user[4]}
"""

        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Admin notification failed: {e}")

        return

# ================= PHOTO =================

async def handle_photo(update: Update, context):
    user_id = update.effective_user.id
    user_data = get_user(user_id)

    if not user_data:
        return

    if user_data[7] == "proof_pending":
        update_user(user_id, "proof_file_id", update.message.photo[-1].file_id)
        update_user(user_id, "current_step", "whatsapp_pending")
        await update.message.reply_text("📱 Now enter your WhatsApp number:")
        return

# ================= MAIN =================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
