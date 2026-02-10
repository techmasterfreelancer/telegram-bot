import logging
import sqlite3
import hashlib
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.constants import ParseMode

# ================= CONFIG =================
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
# ==========================================

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
        status TEXT DEFAULT 'new',
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

# ================= PREMIUM MESSAGES =================

WELCOME_MESSAGE = """
━━━━━━━━━━━━━━━━━━━━━━
🎓 PREMIUM ACCESS PORTAL
━━━━━━━━━━━━━━━━━━━━━━

Welcome {name},

To maintain community quality, we verify all customers before granting access.

━━━━━━━━━━━━━━━━━━━━━━
📌 SELECT YOUR PURCHASE TYPE
━━━━━━━━━━━━━━━━━━━━━━
"""

STEP1 = """
━━━━━━━━━━━━━━━━━━━━━━
STEP 1 OF 4 — FULL NAME
━━━━━━━━━━━━━━━━━━━━━━

Enter your complete name used during purchase.
"""

STEP2 = """
━━━━━━━━━━━━━━━━━━━━━━
STEP 2 OF 4 — EMAIL CONFIRMATION
━━━━━━━━━━━━━━━━━━━━━━

Enter the SAME email used during purchase.
"""

STEP3 = """
━━━━━━━━━━━━━━━━━━━━━━
STEP 3 OF 4 — PURCHASE PROOF
━━━━━━━━━━━━━━━━━━━━━━

Upload clear screenshot of your receipt.
"""

STEP4 = """
━━━━━━━━━━━━━━━━━━━━━━
STEP 4 OF 4 — WHATSAPP NUMBER
━━━━━━━━━━━━━━━━━━━━━━

Enter WhatsApp number with country code.
Example: +923001234567
"""

SUBMITTED = """
━━━━━━━━━━━━━━━━━━━━━━
✅ APPLICATION SUBMITTED
━━━━━━━━━━━━━━━━━━━━━━

Admin will review within 24 hours.
Do not submit multiple requests.
"""

PAYMENT_MSG = f"""
━━━━━━━━━━━━━━━━━━━━━━
💳 PAYMENT REQUIRED
━━━━━━━━━━━━━━━━━━━━━━

Amount: {MEMBERSHIP_FEE}

BINANCE:
Email: {BINANCE_EMAIL}
ID: {BINANCE_ID}
Network: {BINANCE_NETWORK}

EASYPAYSA:
Name: {EASYPAYSA_NAME}
Number: {EASYPAYSA_NUMBER}

After payment upload screenshot here.
"""

SUCCESS_MSG = f"""
━━━━━━━━━━━━━━━━━━━━━━
🏆 PAYMENT VERIFIED
━━━━━━━━━━━━━━━━━━━━━━

Welcome to Premium Community.

Telegram:
{TELEGRAM_GROUP_LINK}

WhatsApp:
{WHATSAPP_GROUP_LINK}
"""

# ================= BOT =================

async def start(update: Update, context):
    user = update.effective_user
    if not get_user(user.id):
        create_user(user.id, user.username or "NoUsername")

    keyboard = [
        [InlineKeyboardButton("💎 Premium Subscription", callback_data="type_premium")],
        [InlineKeyboardButton("🛒 Product Purchase", callback_data="type_product")]
    ]

    await update.message.reply_text(
        WELCOME_MESSAGE.format(name=user.first_name),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data.startswith("type_"):
        t = "Premium Subscription" if "premium" in query.data else "Product Purchase"
        update_user(user_id, "request_type", t)
        update_user(user_id, "current_step", "name_pending")
        await query.edit_message_text(STEP1, parse_mode=ParseMode.MARKDOWN)
        return

    if query.data.startswith("approve_"):
        target = int(query.data.split("_")[1])
        update_user(target, "status", "payment_pending")

        await context.bot.send_message(
            chat_id=target,
            text=PAYMENT_MSG,
            parse_mode=ParseMode.MARKDOWN
        )

        await query.edit_message_text("✅ Approved. Payment instructions sent.")
        return

    if query.data.startswith("reject_"):
        target = int(query.data.split("_")[1])
        await context.bot.send_message(
            chat_id=target,
            text="❌ Application rejected due to invalid information."
        )
        await query.edit_message_text("Rejected.")
        return

    if query.data.startswith("final_"):
        target = int(query.data.split("_")[1])
        update_user(target, "status", "completed")

        await context.bot.send_message(
            chat_id=target,
            text=SUCCESS_MSG,
            parse_mode=ParseMode.MARKDOWN
        )

        await query.edit_message_text("✅ Payment verified & links sent.")
        return

async def handle_text(update: Update, context):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    if not user_data:
        return

    step = user_data[7]
    text = update.message.text

    if step == "name_pending":
        update_user(user_id, "full_name", text)
        update_user(user_id, "current_step", "email_pending")
        await update.message.reply_text(STEP2, parse_mode=ParseMode.MARKDOWN)
        return

    if step == "email_pending":
        update_user(user_id, "email", text)
        update_user(user_id, "current_step", "proof_pending")
        await update.message.reply_text(STEP3, parse_mode=ParseMode.MARKDOWN)
        return

    if step == "whatsapp_pending":
        update_user(user_id, "whatsapp", text)
        update_user(user_id, "current_step", "info_submitted")

        updated = get_user(user_id)

        keyboard = [[
            InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{user_id}")
        ]]

        admin_msg = f"""
🚨 NEW REQUEST

User: @{updated[1]}
ID: {user_id}
Name: {updated[2]}
Email: {updated[3]}
WhatsApp: {updated[4]}
Type: {updated[5]}
"""

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_msg,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        await update.message.reply_text(SUBMITTED, parse_mode=ParseMode.MARKDOWN)

async def handle_photo(update: Update, context):
    user_id = update.effective_user.id
    user_data = get_user(user_id)

    if user_data and user_data[7] == "proof_pending":
        update_user(user_id, "proof_file_id", update.message.photo[-1].file_id)
        update_user(user_id, "current_step", "whatsapp_pending")
        await update.message.reply_text(STEP4, parse_mode=ParseMode.MARKDOWN)

    if user_data and user_data[10] == "payment_pending":
        keyboard = [[
            InlineKeyboardButton("✅ VERIFY PAYMENT", callback_data=f"final_{user_id}")
        ]]

        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=update.message.photo[-1].file_id,
            caption="💰 Payment Screenshot Received",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Premium Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
