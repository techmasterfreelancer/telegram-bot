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
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result

def create_user(user_id, username):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO users (user_id, username, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (user_id, username, datetime.now(), datetime.now())
    )
    conn.commit()
    conn.close()

def update_user(user_id, field, value):
    conn = get_db()
    c = conn.cursor()
    c.execute(f"UPDATE users SET {field}=?, updated_at=? WHERE user_id=?",
              (value, datetime.now(), user_id))
    conn.commit()
    conn.close()

# ================= ADMIN NOTIFICATION FIX =================

async def notify_admin(context, user_id):
    """Guaranteed admin notification"""

    user_data = get_user(user_id)  # Always get fresh data

    if not user_data:
        logger.error("User data not found for admin notification")
        return

    time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    message = f"""
🚨 *NEW APPLICATION RECEIVED*

👤 Username: @{user_data[1]}
🆔 User ID: `{user_id}`
📌 Type: {user_data[5]}

📝 Name: {user_data[2]}
📧 Email: {user_data[3]}
📱 WhatsApp: {user_data[4]}

⏰ Submitted: {time_now}

👇 Approve or Reject:
"""

    keyboard = [
        [
            InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{user_id}")
        ]
    ]

    try:
        if user_data[6]:  # proof exists
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=user_data[6],
                caption=message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )

        logger.info("Admin notification sent successfully")

    except Exception as e:
        logger.error(f"Admin notification failed: {e}")

# ===========================================================

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

async def handle_callback(update: Update, context):
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = update.effective_user.id

    if data.startswith("type_"):
        request_type = "Premium Subscription" if "premium" in data else "Product Purchase"
        update_user(user_id, "request_type", request_type)
        update_user(user_id, "current_step", "name_pending")

        await query.edit_message_text("📝 Enter your FULL NAME:")
        return

    if data.startswith("approve_"):
        target = int(data.split("_")[1])
        update_user(target, "admin_approved", 1)
        update_user(target, "status", "payment_pending")

        await context.bot.send_message(
            chat_id=target,
            text=f"🎉 Approved!\n\nPay {MEMBERSHIP_FEE} to continue."
        )

        await query.edit_message_text("✅ Approved & user notified.")
        return

    if data.startswith("reject_"):
        target = int(data.split("_")[1])
        await context.bot.send_message(
            chat_id=target,
            text="❌ Your application was rejected."
        )
        await query.edit_message_text("❌ Rejected.")
        return

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
        await update.message.reply_text("📱 Enter WhatsApp with country code:")
        return

    if step == "whatsapp_pending":
        update_user(user_id, "whatsapp", text)
        update_user(user_id, "current_step", "info_submitted")

        await update.message.reply_text("✅ Application Submitted!")

        # 🔥 FIXED ADMIN CALL
        await notify_admin(context, user_id)

        return

async def handle_photo(update: Update, context):
    user_id = update.effective_user.id
    file_id = update.message.photo[-1].file_id
    update_user(user_id, "proof_file_id", file_id)
    update_user(user_id, "current_step", "whatsapp_pending")

    await update.message.reply_text("📱 Now enter WhatsApp number:")

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("🤖 Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
