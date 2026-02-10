import logging
import sqlite3
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
        payment_file_id TEXT,
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

# ================= PROFESSIONAL MESSAGES =================

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
Enter the SAME email used for registration.
"""

STEP3 = """
━━━━━━━━━━━━━━━━━━━━━━
STEP 3 OF 4 — PURCHASE PROOF
━━━━━━━━━━━━━━━━━━━━━━
Upload a clear screenshot of your receipt.
"""

STEP4 = """
━━━━━━━━━━━━━━━━━━━━━━
STEP 4 OF 4 — WHATSAPP NUMBER
━━━━━━━━━━━━━━━━━━━━━━
Enter your WhatsApp number with country code.
Example: +923001234567
"""

SUBMITTED = """
━━━━━━━━━━━━━━━━━━━━━━
✅ APPLICATION SUBMITTED
━━━━━━━━━━━━━━━━━━━━━━
Your request is under admin review.
Estimated time: 2–24 hours.
"""

SUCCESS_MESSAGE = """
━━━━━━━━━━━━━━━━━━━━━━
🏆 PREMIUM MEMBERSHIP ACTIVATED
━━━━━━━━━━━━━━━━━━━━━━

Your payment has been verified successfully.

🔐 Private Access Links:

Telegram:
{telegram_link}

WhatsApp:
{whatsapp_link}

Welcome to the Inner Circle.
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
        f"""
━━━━━━━━━━━━━━━━━━━━━━
🎓 PREMIUM ACCESS PORTAL
━━━━━━━━━━━━━━━━━━━━━━

Welcome {user.first_name},

Please select your purchase type.
""",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    data = query.data

    # Admin approve initial info
    if data.startswith("approve_"):
        user_id = int(data.split("_")[1])

        update_user(user_id, "admin_approved", 1)
        update_user(user_id, "status", "payment_pending")

        keyboard = [
            [InlineKeyboardButton("💰 Pay with Binance", callback_data="pay_binance")],
            [InlineKeyboardButton("📱 Pay with Easypaisa", callback_data="pay_easypaisa")]
        ]

        await context.bot.send_message(
            chat_id=user_id,
            text=f"""
━━━━━━━━━━━━━━━━━━━━━━
✅ APPLICATION APPROVED
━━━━━━━━━━━━━━━━━━━━━━

Please complete payment.

Amount: {MEMBERSHIP_FEE}

After payment upload screenshot here.
""",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        await query.edit_message_reply_markup(reply_markup=None)
        return

    # Payment method
    if data.startswith("pay_"):
        if "binance" in data:
            text = f"""
BINANCE PAYMENT

Email: {BINANCE_EMAIL}
ID: {BINANCE_ID}
Network: {BINANCE_NETWORK}
Amount: {MEMBERSHIP_FEE}

Upload payment screenshot after sending.
"""
        else:
            text = f"""
EASYPAYSA PAYMENT

Name: {EASYPAYSA_NAME}
Number: {EASYPAYSA_NUMBER}
Amount: {MEMBERSHIP_FEE}

Upload payment screenshot after sending.
"""
        await query.edit_message_text(text)
        return

    # Final approve payment
    if data.startswith("final_"):
        user_id = int(data.split("_")[1])
        update_user(user_id, "status", "completed")

        await context.bot.send_message(
            chat_id=user_id,
            text=SUCCESS_MESSAGE.format(
                telegram_link=TELEGRAM_GROUP_LINK,
                whatsapp_link=WHATSAPP_GROUP_LINK
            ),
            parse_mode=ParseMode.MARKDOWN
        )

        await query.edit_message_reply_markup(reply_markup=None)
        return

async def handle_text(update: Update, context):
    user_id = update.effective_user.id
    text = update.message.text

    user = get_user(user_id)
    if not user:
        return

    step = user[7]

    if step == "name_pending":
        update_user(user_id, "full_name", text)
        update_user(user_id, "current_step", "email_pending")
        await update.message.reply_text("Enter your email:")
        return

    if step == "email_pending":
        update_user(user_id, "email", text)
        update_user(user_id, "current_step", "proof_pending")
        await update.message.reply_text("Upload purchase screenshot:")
        return

    if step == "whatsapp_pending":
        update_user(user_id, "whatsapp", text)
        update_user(user_id, "current_step", "info_submitted")

        updated = get_user(user_id)

        await update.message.reply_text("Application submitted. Await admin review.")

        keyboard = [[
            InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{user_id}")
        ]]

        admin_text = f"""
━━━━━━━━━━━━━━━━━━━━━━
🆕 NEW PREMIUM REQUEST
━━━━━━━━━━━━━━━━━━━━━━

User: @{updated[1]}
ID: {user_id}

Name: {updated[2]}
Email: {updated[3]}
WhatsApp: {updated[4]}
Type: {updated[5]}

━━━━━━━━━━━━━━━━━━━━━━
Proof attached above.
"""

        if updated[6]:
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=updated[6],
                caption=admin_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return

async def handle_photo(update: Update, context):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        return

    step = user[7]
    status = user[9]

    # First purchase proof
    if step == "proof_pending":
        update_user(user_id, "proof_file_id", update.message.photo[-1].file_id)
        update_user(user_id, "current_step", "whatsapp_pending")
        await update.message.reply_text("Now enter WhatsApp number:")
        return

    # Payment screenshot
    if status == "payment_pending":
        file_id = update.message.photo[-1].file_id
        update_user(user_id, "payment_file_id", file_id)

        await update.message.reply_text("Payment received. Under review.")

        updated = get_user(user_id)

        keyboard = [[
            InlineKeyboardButton("✅ APPROVE & SEND LINKS", callback_data=f"final_{user_id}")
        ]]

        admin_text = f"""
━━━━━━━━━━━━━━━━━━━━━━
💰 PAYMENT VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━

User: @{updated[1]}
ID: {user_id}

Name: {updated[2]}
Email: {updated[3]}
WhatsApp: {updated[4]}

━━━━━━━━━━━━━━━━━━━━━━
Payment screenshot attached above.
"""

        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=file_id,
            caption=admin_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Professional Premium Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
