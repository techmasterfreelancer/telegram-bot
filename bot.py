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

# ================= MESSAGES =================

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

Enter the SAME email used for registration/purchase.
"""

STEP3 = """
━━━━━━━━━━━━━━━━━━━━━━
STEP 3 OF 4 — PURCHASE PROOF
━━━━━━━━━━━━━━━━━━━━━━

Upload a clear screenshot of your receipt or order confirmation.
"""

STEP4 = """
━━━━━━━━━━━━━━━━━━━━━━
STEP 4 OF 4 — WHATSAPP NUMBER
━━━━━━━━━━━━━━━━━━━━━━

Enter your WhatsApp number with country code.

Example:
+923001234567
"""

SUBMITTED = """
━━━━━━━━━━━━━━━━━━━━━━
✅ APPLICATION SUBMITTED
━━━━━━━━━━━━━━━━━━━━━━

Your information has been forwarded for admin review.

Status: Pending Verification
Estimated Time: 2 – 24 hours
"""

SUCCESS_MESSAGE = """
━━━━━━━━━━━━━━━━━━━━━━
🏆 PREMIUM MEMBERSHIP ACTIVATED
━━━━━━━━━━━━━━━━━━━━━━

Your payment has been verified.

🔐 Private Access Links:

Telegram:
{telegram_link}

WhatsApp:
{whatsapp_link}

Welcome to the Inner Circle.
"""

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
        WELCOME_MESSAGE.format(name=user.first_name),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

# ================= CALLBACK HANDLER =================

async def handle_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    # TYPE SELECT
    if data.startswith("type_"):
        t = "Premium Subscription" if "premium" in data else "Product Purchase"
        update_user(user_id, "request_type", t)
        update_user(user_id, "current_step", "name_pending")
        await query.edit_message_text(STEP1, parse_mode=ParseMode.MARKDOWN)
        return

    # ADMIN APPROVE APPLICATION
    if data.startswith("approve_"):
        target = int(data.split("_")[1])

        update_user(target, "admin_approved", 1)
        update_user(target, "status", "payment_pending")

        keyboard = [
            [InlineKeyboardButton("💰 Binance", callback_data="pay_binance")],
            [InlineKeyboardButton("📱 Easypaisa", callback_data="pay_easypaisa")]
        ]

        await context.bot.send_message(
            chat_id=target,
            text=f"🎉 APPROVED!\n\nMembership Fee: {MEMBERSHIP_FEE}\n\nSelect payment method:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        # REMOVE BUTTONS
        await query.edit_message_reply_markup(reply_markup=None)
        return

    # ADMIN REJECT APPLICATION
    if data.startswith("reject_"):
        target = int(data.split("_")[1])

        await context.bot.send_message(
            chat_id=target,
            text="❌ Your application has been rejected."
        )

        await query.edit_message_reply_markup(reply_markup=None)
        return

    # PAYMENT METHOD SELECT
    if data.startswith("pay_"):
        if "binance" in data:
            text = f"""
💰 BINANCE PAYMENT

Email: {BINANCE_EMAIL}
ID: {BINANCE_ID}
Network: {BINANCE_NETWORK}
Amount: {MEMBERSHIP_FEE}
"""
        else:
            text = f"""
📱 EASYPAYSA PAYMENT

Name: {EASYPAYSA_NAME}
Number: {EASYPAYSA_NUMBER}
Amount: {MEMBERSHIP_FEE}
"""
        await query.edit_message_text(text)
        return

    # FINAL APPROVE PAYMENT
    if data.startswith("final_"):
        target = int(data.split("_")[1])

        update_user(target, "status", "completed")

        await context.bot.send_message(
            chat_id=target,
            text=SUCCESS_MESSAGE.format(
                telegram_link=TELEGRAM_GROUP_LINK,
                whatsapp_link=WHATSAPP_GROUP_LINK
            ),
            parse_mode=ParseMode.MARKDOWN
        )

        await query.edit_message_reply_markup(reply_markup=None)
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

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"""
🚨 NEW PREMIUM REQUEST

Name: {updated[2]}
Email: {updated[3]}
WhatsApp: {updated[4]}
Type: {updated[5]}
""",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        await update.message.reply_text(SUBMITTED, parse_mode=ParseMode.MARKDOWN)
        return

# ================= PHOTO =================

async def handle_photo(update: Update, context):
    user_id = update.effective_user.id
    user_data = get_user(user_id)

    if user_data and user_data[7] == "proof_pending":
        update_user(user_id, "proof_file_id", update.message.photo[-1].file_id)
        update_user(user_id, "current_step", "whatsapp_pending")
        await update.message.reply_text(STEP4, parse_mode=ParseMode.MARKDOWN)

# ================= MAIN =================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Premium Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
