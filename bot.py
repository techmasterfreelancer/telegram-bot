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
        payment_file_id TEXT,
        current_step TEXT DEFAULT 'start',
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

# ==========================================================
# ===== START: WELCOME MESSAGE =============================
# ==========================================================

WELCOME_MESSAGE = """
━━━━━━━━━━━━━━━━━━━━━━
🎓 PREMIUM ACCESS PORTAL
━━━━━━━━━━━━━━━━━━━━━━

Welcome {name},

To maintain high community standards,
all purchases are verified before access.

━━━━━━━━━━━━━━━━━━━━━━
📌 SELECT YOUR PURCHASE TYPE
━━━━━━━━━━━━━━━━━━━━━━
"""
# ===== END: WELCOME MESSAGE ===============================


# ==========================================================
# ===== START: STEP 1 MESSAGE ==============================
# ==========================================================

STEP_1_MESSAGE = """
━━━━━━━━━━━━━━━━━━━━━━
STEP 1 OF 4 — FULL NAME
━━━━━━━━━━━━━━━━━━━━━━

Enter your complete name used during purchase.
"""
# ===== END: STEP 1 MESSAGE ================================


# ==========================================================
# ===== START: STEP 2 MESSAGE ==============================
# ==========================================================

STEP_2_MESSAGE = """
━━━━━━━━━━━━━━━━━━━━━━
STEP 2 OF 4 — EMAIL CONFIRMATION
━━━━━━━━━━━━━━━━━━━━━━

Enter the SAME email used for purchase.
"""
# ===== END: STEP 2 MESSAGE ================================


# ==========================================================
# ===== START: STEP 3 MESSAGE ==============================
# ==========================================================

STEP_3_MESSAGE = """
━━━━━━━━━━━━━━━━━━━━━━
STEP 3 OF 4 — PURCHASE PROOF
━━━━━━━━━━━━━━━━━━━━━━

Upload a clear screenshot of your receipt.
"""
# ===== END: STEP 3 MESSAGE ================================


# ==========================================================
# ===== START: STEP 4 MESSAGE ==============================
# ==========================================================

STEP_4_MESSAGE = """
━━━━━━━━━━━━━━━━━━━━━━
STEP 4 OF 4 — WHATSAPP NUMBER
━━━━━━━━━━━━━━━━━━━━━━

Enter your WhatsApp number with country code.
"""
# ===== END: STEP 4 MESSAGE ================================


# ==========================================================
# ===== START: APPLICATION SUBMITTED MESSAGE ===============
# ==========================================================

APPLICATION_SUBMITTED_MESSAGE = """
━━━━━━━━━━━━━━━━━━━━━━
✅ APPLICATION SUBMITTED
━━━━━━━━━━━━━━━━━━━━━━

Your information has been sent for review.

Estimated approval time: 2–24 hours.
"""
# ===== END: APPLICATION SUBMITTED MESSAGE =================


# ==========================================================
# ===== START: PAYMENT UNDER REVIEW MESSAGE ================
# ==========================================================

PAYMENT_REVIEW_MESSAGE = """
━━━━━━━━━━━━━━━━━━━━━━
⏳ PAYMENT UNDER REVIEW
━━━━━━━━━━━━━━━━━━━━━━

Your payment screenshot has been received.

Admin is verifying it now.
"""
# ===== END: PAYMENT UNDER REVIEW MESSAGE ==================


# ==========================================================
# ===== START: FINAL SUCCESS MESSAGE =======================
# ==========================================================

FINAL_SUCCESS_MESSAGE = """
━━━━━━━━━━━━━━━━━━━━━━
🏆 PREMIUM MEMBERSHIP ACTIVATED
━━━━━━━━━━━━━━━━━━━━━━

Your payment has been verified.

Telegram:
{telegram_link}

WhatsApp:
{whatsapp_link}

Welcome to the Inner Circle.
"""
# ===== END: FINAL SUCCESS MESSAGE =========================


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
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("type_"):
        user_id = query.from_user.id
        purchase_type = "Premium Subscription" if "premium" in data else "Product Purchase"
        update_user(user_id, "request_type", purchase_type)
        update_user(user_id, "current_step", "name_pending")
        await query.edit_message_text(STEP_1_MESSAGE)
        return

    if data.startswith("approve_"):
        user_id = int(data.split("_")[1])
        update_user(user_id, "status", "payment_pending")

        keyboard = [
            [InlineKeyboardButton("💰 Pay with Binance", callback_data="pay_binance")],
            [InlineKeyboardButton("📱 Pay with Easypaisa", callback_data="pay_easypaisa")]
        ]

        await context.bot.send_message(
            chat_id=user_id,
            text=f"Your application is approved.\n\nAmount: {MEMBERSHIP_FEE}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        await query.edit_message_reply_markup(None)
        return

    if data.startswith("pay_"):
        if "binance" in data:
            text = f"BINANCE\nEmail: {BINANCE_EMAIL}\nID: {BINANCE_ID}\nAmount: {MEMBERSHIP_FEE}"
        else:
            text = f"EASYPAYSA\nName: {EASYPAYSA_NAME}\nNumber: {EASYPAYSA_NUMBER}\nAmount: {MEMBERSHIP_FEE}"
        await query.edit_message_text(text)
        return

    if data.startswith("final_"):
        user_id = int(data.split("_")[1])
        update_user(user_id, "status", "completed")

        await context.bot.send_message(
            chat_id=user_id,
            text=FINAL_SUCCESS_MESSAGE.format(
                telegram_link=TELEGRAM_GROUP_LINK,
                whatsapp_link=WHATSAPP_GROUP_LINK
            ),
            parse_mode=ParseMode.MARKDOWN
        )

        await query.edit_message_reply_markup(None)
        return

async def handle_text(update: Update, context):
    user_id = update.effective_user.id
    text = update.message.text
    user = get_user(user_id)

    if not user:
        return

    step = user[8]

    if step == "name_pending":
        update_user(user_id, "full_name", text)
        update_user(user_id, "current_step", "email_pending")
        await update.message.reply_text(STEP_2_MESSAGE)
        return

    if step == "email_pending":
        update_user(user_id, "email", text)
        update_user(user_id, "current_step", "proof_pending")
        await update.message.reply_text(STEP_3_MESSAGE)
        return

    if step == "whatsapp_pending":
        update_user(user_id, "whatsapp", text)
        update_user(user_id, "current_step", "info_submitted")
        await update.message.reply_text(APPLICATION_SUBMITTED_MESSAGE)

        keyboard = [[InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{user_id}")]]
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"New request from @{user[1]}\nUser ID: {user_id}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

async def handle_photo(update: Update, context):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        return

    step = user[8]
    status = user[9]

    if step == "proof_pending":
        update_user(user_id, "proof_file_id", update.message.photo[-1].file_id)
        update_user(user_id, "current_step", "whatsapp_pending")
        await update.message.reply_text(STEP_4_MESSAGE)
        return

    if status == "payment_pending":
        update_user(user_id, "payment_file_id", update.message.photo[-1].file_id)
        await update.message.reply_text(PAYMENT_REVIEW_MESSAGE)

        keyboard = [[InlineKeyboardButton("✅ APPROVE & SEND LINKS", callback_data=f"final_{user_id}")]]
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=update.message.photo[-1].file_id,
            caption="Payment received for verification",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

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
