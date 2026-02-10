import logging
import sqlite3
import re
import hashlib
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

# ================= DATABASE =================
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
        payment_file_id TEXT,
        current_step TEXT,
        status TEXT
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

def update_user(user_id, field, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"UPDATE users SET {field}=? WHERE user_id=?", (value, user_id))
    conn.commit()
    conn.close()

def create_user(user_id, username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, current_step, status) VALUES (?, ?, ?, ?)",
              (user_id, username, "start", "new"))
    conn.commit()
    conn.close()

# ================= PREMIUM MESSAGE BLOCKS =================

WELCOME_BLOCK = """
━━━━━━━━━━━━━━━━━━━━━━
🎓 PREMIUM ACCESS PORTAL
━━━━━━━━━━━━━━━━━━━━━━

Welcome {name},

To maintain quality and security of our private community,
all members go through a short verification process.

Please select your purchase type below.
━━━━━━━━━━━━━━━━━━━━━━
"""

SUBMIT_SUCCESS_BLOCK = """
━━━━━━━━━━━━━━━━━━━━━━
✅ APPLICATION SUBMITTED
━━━━━━━━━━━━━━━━━━━━━━

Your details have been forwarded to our verification team.

⏳ Review Time: 2–24 Hours
📩 You will receive approval notification here.

Please wait patiently.
━━━━━━━━━━━━━━━━━━━━━━
"""

BILLING_BLOCK = """
━━━━━━━━━━━━━━━━━━━━━━
💳 PREMIUM MEMBERSHIP BILLING
━━━━━━━━━━━━━━━━━━━━━━

To activate your Lifetime Premium Access:

💎 Fee: {fee}

Please select your payment method below.

After payment,
upload your payment screenshot here.

━━━━━━━━━━━━━━━━━━━━━━
"""

FINAL_SUCCESS_BLOCK = """
━━━━━━━━━━━━━━━━━━━━━━
🏆 MEMBERSHIP ACTIVATED
━━━━━━━━━━━━━━━━━━━━━━

Congratulations!

Your payment has been verified successfully.

🔐 Access Links:

Telegram:
{telegram}

WhatsApp:
{whatsapp}

Welcome to the Inner Circle.
━━━━━━━━━━━━━━━━━━━━━━
"""

# ================= BOT LOGIC =================

async def start(update: Update, context):
    user = update.effective_user
    create_user(user.id, user.username or "NoUsername")

    keyboard = [
        [InlineKeyboardButton("💎 Premium Subscription", callback_data="type_premium")],
        [InlineKeyboardButton("🛒 Product Purchase", callback_data="type_product")]
    ]

    await update.message.reply_text(
        WELCOME_BLOCK.format(name=user.first_name),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data = get_user(user_id)

    if query.data.startswith("type_"):
        purchase = "Premium Subscription" if "premium" in query.data else "Product Purchase"
        update_user(user_id, "request_type", purchase)
        update_user(user_id, "current_step", "name")
        await query.edit_message_text("Enter your Full Name:")
        return

    if query.data.startswith("approve_"):
        target = int(query.data.split("_")[1])

        billing_keyboard = [
            [InlineKeyboardButton("💰 Binance", callback_data="pay_binance")],
            [InlineKeyboardButton("📱 Easypaisa", callback_data="pay_easypaisa")]
        ]

        await context.bot.send_message(
            chat_id=target,
            text=BILLING_BLOCK.format(fee=MEMBERSHIP_FEE),
            reply_markup=InlineKeyboardMarkup(billing_keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

        await query.edit_message_reply_markup(reply_markup=None)
        return

    if query.data.startswith("finalapprove_"):
        target = int(query.data.split("_")[1])

        await context.bot.send_message(
            chat_id=target,
            text=FINAL_SUCCESS_BLOCK.format(
                telegram=TELEGRAM_GROUP_LINK,
                whatsapp=WHATSAPP_GROUP_LINK
            ),
            parse_mode=ParseMode.MARKDOWN
        )

        await query.edit_message_reply_markup(reply_markup=None)
        return

async def handle_text(update: Update, context):
    user_id = update.effective_user.id
    text = update.message.text
    user_data = get_user(user_id)

    step = user_data[8]

    if step == "name":
        update_user(user_id, "full_name", text)
        update_user(user_id, "current_step", "email")
        await update.message.reply_text("Enter your Email:")
        return

    if step == "email":
        update_user(user_id, "email", text)
        update_user(user_id, "current_step", "proof")
        await update.message.reply_text("Upload Purchase Screenshot:")
        return

    if step == "whatsapp":
        update_user(user_id, "whatsapp", text)
        update_user(user_id, "current_step", "submitted")

        await update.message.reply_text(SUBMIT_SUCCESS_BLOCK, parse_mode=ParseMode.MARKDOWN)

        keyboard = [[
            InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{user_id}")
        ]]

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"New Request from @{user_data[1]}\nID: {user_id}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_photo(update: Update, context):
    user_id = update.effective_user.id
    user_data = get_user(user_id)

    if user_data[8] == "proof":
        update_user(user_id, "proof_file_id", update.message.photo[-1].file_id)
        update_user(user_id, "current_step", "whatsapp")
        await update.message.reply_text("Enter WhatsApp Number:")
        return

    if user_data[8] == "payment":
        update_user(user_id, "payment_file_id", update.message.photo[-1].file_id)

        keyboard = [[
            InlineKeyboardButton("✅ FINAL APPROVE", callback_data=f"finalapprove_{user_id}")
        ]]

        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=update.message.photo[-1].file_id,
            caption=f"Payment received from @{user_data[1]}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Premium Stable Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
