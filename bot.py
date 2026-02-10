import logging
import sqlite3
import hashlib
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

# ================== CONFIG ==================

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

DB_PATH = "bot.db"

# ============================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= DATABASE =================

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        email TEXT,
        whatsapp TEXT,
        request_type TEXT,
        proof_file_id TEXT,
        payment_method TEXT,
        payment_file_id TEXT,
        payment_hash TEXT,
        status TEXT DEFAULT 'new',
        step TEXT DEFAULT 'start',
        created_at TIMESTAMP
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS screenshots(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_hash TEXT UNIQUE,
        user_id INTEGER
    )
    """)
    conn.commit()
    conn.close()

init_db()

def db():
    return sqlite3.connect(DB_PATH)

def get_user(uid):
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    r = c.fetchone()
    conn.close()
    return r

def update_user(uid, field, value):
    conn = db()
    c = conn.cursor()
    c.execute(f"UPDATE users SET {field}=? WHERE user_id=?", (value, uid))
    conn.commit()
    conn.close()

# ================= MESSAGES =================

WELCOME = """
━━━━━━━━━━━━━━━━━━━━━━
🎓 PREMIUM ACCESS PORTAL
━━━━━━━━━━━━━━━━━━━━━━

Welcome {name},

This system verifies genuine customers 
before granting premium access.

━━━━━━━━━━━━━━━━━━━━━━
Select your purchase type:
"""

SUCCESS = """
━━━━━━━━━━━━━━━━━━━━━━
🏆 PAYMENT VERIFIED
━━━━━━━━━━━━━━━━━━━━━━

Congratulations {name},

Your Premium Membership is ACTIVE.

🔐 Telegram:
{tg}

📱 WhatsApp:
{wa}

Welcome to the Inner Circle.
"""

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id

    if not get_user(uid):
        conn = db()
        c = conn.cursor()
        c.execute("INSERT INTO users(user_id,username,created_at) VALUES(?,?,?)",
                  (uid, user.username, datetime.now()))
        conn.commit()
        conn.close()

    keyboard = [
        [InlineKeyboardButton("💎 Premium Subscription", callback_data="type_premium")],
        [InlineKeyboardButton("🛒 Product Purchase", callback_data="type_product")]
    ]

    await update.message.reply_text(
        WELCOME.format(name=user.first_name),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

# ================= CALLBACK =================

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid = update.effective_user.id

    # TYPE SELECT
    if data.startswith("type_"):
        t = "Premium Subscription" if "premium" in data else "Product Purchase"
        update_user(uid, "request_type", t)
        update_user(uid, "step", "name")

        await query.edit_message_text(
            "STEP 1/4\n\nEnter your FULL NAME:",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # ADMIN APPROVE APPLICATION
    if data.startswith("approve_"):
        target = int(data.split("_")[1])
        update_user(target, "status", "payment_pending")
        update_user(target, "step", "payment")

        keyboard = [
            [InlineKeyboardButton("💰 Binance", callback_data="pay_binance")],
            [InlineKeyboardButton("📱 Easypaisa", callback_data="pay_easypaisa")]
        ]

        await context.bot.send_message(
            chat_id=target,
            text=f"Application Approved.\n\nMembership Fee: {MEMBERSHIP_FEE}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        await query.edit_message_reply_markup(reply_markup=None)
        await query.edit_message_text("Application Approved ✅")
        return

    # PAYMENT METHOD
    if data.startswith("pay_"):
        method = data.split("_")[1]
        update_user(uid, "payment_method", method)

        if method == "binance":
            text = f"Send {MEMBERSHIP_FEE} to:\n{BINANCE_EMAIL}\nUID: {BINANCE_ID}\nNetwork: {BINANCE_NETWORK}"
        else:
            text = f"Send {MEMBERSHIP_FEE} to:\n{EASYPAYSA_NAME}\n{EASYPAYSA_NUMBER}"

        await query.edit_message_text(text)
        return

    # FINAL APPROVE PAYMENT
    if data.startswith("final_"):
        target = int(data.split("_")[1])
        user_data = get_user(target)

        update_user(target, "status", "completed")

        await context.bot.send_message(
            chat_id=target,
            text=SUCCESS.format(
                name=user_data[2],
                tg=TELEGRAM_GROUP_LINK,
                wa=WHATSAPP_GROUP_LINK
            ),
            parse_mode=ParseMode.MARKDOWN
        )

        await query.edit_message_reply_markup(reply_markup=None)
        await query.edit_message_text("Payment Approved & Links Sent ✅")
        return

# ================= TEXT =================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user(uid)
    if not user:
        return

    step = user[11]
    text = update.message.text

    if step == "name":
        update_user(uid, "full_name", text)
        update_user(uid, "step", "email")
        await update.message.reply_text("STEP 2/4\n\nEnter your EMAIL:")
        return

    if step == "email":
        if "@" not in text:
            await update.message.reply_text("Invalid Email")
            return
        update_user(uid, "email", text)
        update_user(uid, "step", "whatsapp")
        await update.message.reply_text("STEP 3/4\n\nEnter WhatsApp (+countrycode):")
        return

    if step == "whatsapp":
        update_user(uid, "whatsapp", text)
        update_user(uid, "status", "review")
        update_user(uid, "step", "done")

        keyboard = [
            [
                InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{uid}"),
            ]
        ]

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"New Application\nID: {uid}\nName: {user[2]}\nEmail: {user[3]}\nWhatsApp: {text}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        await update.message.reply_text("Application Submitted. Wait for admin approval.")
        return

# ================= PHOTO =================

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user(uid)
    if not user:
        return

    if user[10] == "payment_pending":
        photo = update.message.photo[-1]
        file = await photo.get_file()
        data = await file.download_as_bytearray()
        h = hashlib.md5(data).hexdigest()

        conn = db()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO screenshots(file_hash,user_id) VALUES(?,?)", (h, uid))
            conn.commit()
        except:
            await update.message.reply_text("Duplicate Screenshot ❌")
            conn.close()
            return
        conn.close()

        keyboard = [
            [InlineKeyboardButton("✅ APPROVE PAYMENT", callback_data=f"final_{uid}")]
        ]

        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo.file_id,
            caption=f"Payment Proof from {uid}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        await update.message.reply_text("Payment Submitted. Verification in progress.")

# ================= MAIN =================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    print("Premium Professional Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
