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
        status TEXT DEFAULT 'new'
    )''')
    conn.commit()
    conn.close()

init_db()

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    data = c.fetchone()
    conn.close()
    return data

def create_user(user_id, username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?,?)",
              (user_id, username))
    conn.commit()
    conn.close()

def update_user(user_id, field, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"UPDATE users SET {field}=? WHERE user_id=?",
              (value, user_id))
    conn.commit()
    conn.close()

# ================= PREMIUM MESSAGES =================

WELCOME_MESSAGE = """
━━━━━━━━━━━━━━━━━━━━━━
🎓 PREMIUM ACCESS PORTAL
━━━━━━━━━━━━━━━━━━━━━━

Welcome {name},

Select your purchase type to continue verification.
"""

STEP1 = "STEP 1/4 — Enter your FULL NAME"
STEP2 = "STEP 2/4 — Enter your EMAIL"
STEP3 = "STEP 3/4 — Upload Purchase Screenshot"
STEP4 = "STEP 4/4 — Enter WhatsApp with country code"

SUBMITTED = """
━━━━━━━━━━━━━━━━━━━━━━
✅ APPLICATION SUBMITTED
━━━━━━━━━━━━━━━━━━━━━━

Your information has been sent for admin review.

Status: Pending
Time: 2–24 hours
"""

SUCCESS_MESSAGE = """
━━━━━━━━━━━━━━━━━━━━━━
🏆 MEMBERSHIP ACTIVATED
━━━━━━━━━━━━━━━━━━━━━━

Congratulations!

Telegram:
{telegram}

WhatsApp:
{whatsapp}

Welcome to Premium Community.
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

async def handle_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # Type selection
    if query.data.startswith("type_"):
        t = "Premium Subscription" if "premium" in query.data else "Product Purchase"
        update_user(user_id, "request_type", t)
        update_user(user_id, "current_step", "name")
        await query.edit_message_text(STEP1)
        return

    # ADMIN APPROVE FIRST STEP
    if query.data.startswith("approve_"):
        target = int(query.data.split("_")[1])
        update_user(target, "status", "payment_pending")

        keyboard = [
            [InlineKeyboardButton("💰 Pay with Binance", callback_data=f"pay_binance_{target}")],
            [InlineKeyboardButton("📱 Pay with Easypaisa", callback_data=f"pay_easypaisa_{target}")]
        ]

        msg = f"""
🎉 APPLICATION APPROVED

Membership Fee: {MEMBERSHIP_FEE}

Select payment method below.
"""

        await context.bot.send_message(target, msg,
            reply_markup=InlineKeyboardMarkup(keyboard))
        await query.edit_message_text("Approved. Payment options sent.")
        return

    # PAYMENT METHOD
    if query.data.startswith("pay_binance_"):
        target = int(query.data.split("_")[2])
        update_user(target, "payment_method", "Binance")
        await context.bot.send_message(target,
            f"Send {MEMBERSHIP_FEE} to:\nEmail: {BINANCE_EMAIL}\nAfter payment upload screenshot.")
        return

    if query.data.startswith("pay_easypaisa_"):
        target = int(query.data.split("_")[2])
        update_user(target, "payment_method", "Easypaisa")
        await context.bot.send_message(target,
            f"Send {MEMBERSHIP_FEE} to:\nAccount: {EASYPAYSA_NUMBER}\nAfter payment upload screenshot.")
        return

    # FINAL VERIFY
    if query.data.startswith("final_"):
        target = int(query.data.split("_")[1])
        update_user(target, "status", "completed")

        await context.bot.send_message(
            target,
            SUCCESS_MESSAGE.format(
                telegram=TELEGRAM_GROUP_LINK,
                whatsapp=WHATSAPP_GROUP_LINK
            ),
            parse_mode=ParseMode.MARKDOWN
        )

        await query.edit_message_text("Payment verified. Access granted.")
        return

async def handle_text(update: Update, context):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        return

    step = user[7]

    if step == "name":
        update_user(user_id, "full_name", update.message.text)
        update_user(user_id, "current_step", "email")
        await update.message.reply_text(STEP2)
        return

    if step == "email":
        update_user(user_id, "email", update.message.text)
        update_user(user_id, "current_step", "proof")
        await update.message.reply_text(STEP3)
        return

    if step == "whatsapp":
        update_user(user_id, "whatsapp", update.message.text)
        update_user(user_id, "current_step", "submitted")
        await update.message.reply_text(SUBMITTED)

        data = get_user(user_id)

        keyboard = [[
            InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{user_id}")
        ]]

        await context.bot.send_message(
            ADMIN_ID,
            f"New Request\n\nName: {data[2]}\nEmail: {data[3]}\nWhatsApp: {data[4]}\nType: {data[5]}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

async def handle_photo(update: Update, context):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        return

    if user[7] == "proof":
        update_user(user_id, "proof_file_id", update.message.photo[-1].file_id)
        update_user(user_id, "current_step", "whatsapp")
        await update.message.reply_text(STEP4)
        return

    if user[9] and user[10] == "payment_pending":
        keyboard = [[InlineKeyboardButton("✅ VERIFY & ACTIVATE",
                                          callback_data=f"final_{user_id}")]]
        await context.bot.send_photo(
            ADMIN_ID,
            update.message.photo[-1].file_id,
            caption=f"Payment from {user[2]}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await update.message.reply_text("Payment submitted. Await verification.")
        return

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    app.run_polling()

if __name__ == "__main__":
    main()
