import logging
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.constants import ParseMode

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

logging.basicConfig(level=logging.INFO)

DB = "bot.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        email TEXT,
        whatsapp TEXT,
        request_type TEXT,
        proof_file TEXT,
        payment_file TEXT,
        step TEXT
    )""")
    conn.commit()
    conn.close()

init_db()

def get_user(uid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    data = c.fetchone()
    conn.close()
    return data

def update_user(uid, field, value):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(f"UPDATE users SET {field}=? WHERE user_id=?", (value, uid))
    conn.commit()
    conn.close()

def create_user(uid, username):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, step) VALUES (?, ?, ?)", (uid, username, "start"))
    conn.commit()
    conn.close()

# ================= PREMIUM MESSAGE BLOCKS =================

WELCOME_MESSAGE = """
━━━━━━━━━━━━━━━━━━━━━━
🎓 PREMIUM ACCESS PORTAL
━━━━━━━━━━━━━━━━━━━━━━

Welcome {name},

To maintain the quality and exclusivity of our private premium community,
all members must complete a short verification process.

Please select your purchase type below to begin.

━━━━━━━━━━━━━━━━━━━━━━
"""

SUBMIT_MESSAGE = """
━━━━━━━━━━━━━━━━━━━━━━
✅ APPLICATION SUBMITTED
━━━━━━━━━━━━━━━━━━━━━━

Your details have been successfully submitted
to our verification team.

⏳ Review Time: 2–24 Hours
📩 You will receive approval notification here.

Please do not resubmit multiple times.
━━━━━━━━━━━━━━━━━━━━━━
"""

BILLING_MESSAGE = """
━━━━━━━━━━━━━━━━━━━━━━
💳 PREMIUM MEMBERSHIP ACTIVATION
━━━━━━━━━━━━━━━━━━━━━━

Congratulations!

Your application has been approved.

To activate your Lifetime Premium Access:

💎 Membership Fee: {fee}

Select your preferred payment method below.

After payment,
upload your payment screenshot here.

━━━━━━━━━━━━━━━━━━━━━━
"""

PAYMENT_RECEIVED_MESSAGE = """
━━━━━━━━━━━━━━━━━━━━━━
⏳ PAYMENT UNDER REVIEW
━━━━━━━━━━━━━━━━━━━━━━

Your payment screenshot has been received.

Our admin team will verify your payment
within 2–24 hours.

You will receive confirmation once verified.

━━━━━━━━━━━━━━━━━━━━━━
"""

FINAL_SUCCESS_MESSAGE = """
━━━━━━━━━━━━━━━━━━━━━━
🏆 MEMBERSHIP ACTIVATED
━━━━━━━━━━━━━━━━━━━━━━

Congratulations!

Your payment has been successfully verified.

🔐 Exclusive Access Links:

Telegram Group:
{telegram}

WhatsApp Community:
{whatsapp}

Welcome to the Premium Inner Circle.
━━━━━━━━━━━━━━━━━━━━━━
"""

# ================= START =================

async def start(update: Update, context):
    user = update.effective_user
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

# ================= CALLBACK =================

async def callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if query.data.startswith("type_"):
        purchase = "Premium Subscription" if "premium" in query.data else "Product Purchase"
        update_user(uid, "request_type", purchase)
        update_user(uid, "step", "name")
        await query.edit_message_text("Please enter your Full Name:")
        return

    # FIRST APPROVAL
    if query.data.startswith("approve_"):
        target = int(query.data.split("_")[1])

        keyboard = [
            [InlineKeyboardButton("💰 Binance", callback_data=f"pay_binance_{target}")],
            [InlineKeyboardButton("📱 Easypaisa", callback_data=f"pay_easy_{target}")]
        ]

        await context.bot.send_message(
            chat_id=target,
            text=BILLING_MESSAGE.format(fee=MEMBERSHIP_FEE),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

        await query.edit_message_reply_markup(reply_markup=None)
        return

    # PAYMENT METHOD SELECT
    if query.data.startswith("pay_binance_"):
        target = int(query.data.split("_")[2])
        update_user(target, "step", "payment")

        await context.bot.send_message(
            chat_id=target,
            text=f"""
💰 *BINANCE PAYMENT DETAILS*

Email: `{BINANCE_EMAIL}`
Binance ID: `{BINANCE_ID}`
Network: `{BINANCE_NETWORK}`
Amount: {MEMBERSHIP_FEE}

After payment upload screenshot.
""",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if query.data.startswith("pay_easy_"):
        target = int(query.data.split("_")[2])
        update_user(target, "step", "payment")

        await context.bot.send_message(
            chat_id=target,
            text=f"""
📱 *EASYPAYSA PAYMENT DETAILS*

Name: {EASYPAYSA_NAME}
Number: `{EASYPAYSA_NUMBER}`
Amount: {MEMBERSHIP_FEE}

After payment upload screenshot.
""",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # FINAL APPROVAL
    if query.data.startswith("final_"):
        target = int(query.data.split("_")[1])

        await context.bot.send_message(
            chat_id=target,
            text=FINAL_SUCCESS_MESSAGE.format(
                telegram=TELEGRAM_GROUP_LINK,
                whatsapp=WHATSAPP_GROUP_LINK
            ),
            parse_mode=ParseMode.MARKDOWN
        )

        await query.edit_message_reply_markup(reply_markup=None)
        return

# ================= TEXT =================

async def text_handler(update: Update, context):
    uid = update.effective_user.id
    user = get_user(uid)
    step = user[8]

    if step == "name":
        update_user(uid, "full_name", update.message.text)
        update_user(uid, "step", "email")
        await update.message.reply_text("Please enter your Email:")
        return

    if step == "email":
        update_user(uid, "email", update.message.text)
        update_user(uid, "step", "whatsapp")
        await update.message.reply_text("Please enter your WhatsApp number:")
        return

    if step == "whatsapp":
        update_user(uid, "whatsapp", update.message.text)
        update_user(uid, "step", "done")

        user = get_user(uid)

        keyboard = [[
            InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{uid}"),
            InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{uid}")
        ]]

        caption = f"""
📌 *NEW PREMIUM APPLICATION*

Username: @{user[1]}
User ID: {uid}
Name: {user[2]}
Email: {user[3]}
WhatsApp: {user[4]}
Type: {user[5]}
Submitted: {datetime.now().strftime("%Y-%m-%d %H:%M")}
"""

        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=user[6],
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

        await update.message.reply_text(SUBMIT_MESSAGE, parse_mode=ParseMode.MARKDOWN)
        return

# ================= PHOTO =================

async def photo_handler(update: Update, context):
    uid = update.effective_user.id
    user = get_user(uid)
    step = user[8]

    if step == "proof":
        update_user(uid, "proof_file", update.message.photo[-1].file_id)
        update_user(uid, "step", "whatsapp")
        await update.message.reply_text("Please enter your WhatsApp number:")
        return

    if step == "payment":
        update_user(uid, "payment_file", update.message.photo[-1].file_id)

        user = get_user(uid)

        keyboard = [[
            InlineKeyboardButton("✅ FINAL APPROVE", callback_data=f"final_{uid}")
        ]]

        caption = f"""
💰 *PAYMENT SUBMITTED*

Username: @{user[1]}
User ID: {uid}
Name: {user[2]}
Email: {user[3]}
WhatsApp: {user[4]}
Submitted: {datetime.now().strftime("%Y-%m-%d %H:%M")}
"""

        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=update.message.photo[-1].file_id,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

        await update.message.reply_text(PAYMENT_RECEIVED_MESSAGE, parse_mode=ParseMode.MARKDOWN)

# ================= MAIN =================

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    print("Premium Stable Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
