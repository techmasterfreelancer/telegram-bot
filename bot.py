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

def init():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        email TEXT,
        whatsapp TEXT,
        request_type TEXT,
        proof TEXT,
        payment_proof TEXT,
        payment_method TEXT,
        step TEXT,
        status TEXT
    )''')
    conn.commit()
    conn.close()

init()

def get_user(uid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    u = c.fetchone()
    conn.close()
    return u

def update(uid, field, val):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(f"UPDATE users SET {field}=? WHERE user_id=?", (val, uid))
    conn.commit()
    conn.close()

def create(uid, username):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users(user_id,username,step,status) VALUES(?,?,?,?)",
              (uid, username, "name", "new"))
    conn.commit()
    conn.close()

# ================= START =================

async def start(update: Update, context):
    u = update.effective_user
    if not get_user(u.id):
        create(u.id, u.username or "NoUsername")

    keyboard = [
        [InlineKeyboardButton("💎 Premium Subscription", callback_data="type_premium")],
        [InlineKeyboardButton("🛒 Product Purchase", callback_data="type_product")]
    ]

    await update.message.reply_text(f"""
━━━━━━━━━━━━━━━━━━━━━━
🎓 PREMIUM ACCESS PORTAL
━━━━━━━━━━━━━━━━━━━━━━

Welcome {u.first_name},

To maintain community quality, we verify every customer.

Select your purchase type below to begin verification.
""", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= CALLBACK =================

async def callback(update: Update, context):
    q = update.callback_query
    await q.answer()
    data = q.data

    # Purchase type
    if data.startswith("type_"):
        update(q.from_user.id, "request_type",
               "Premium Subscription" if "premium" in data else "Product Purchase")
        update(q.from_user.id, "step", "name")
        await q.edit_message_text("""
━━━━━━━━━━━━━━━━━━━━━━
STEP 1 OF 4 — FULL NAME
━━━━━━━━━━━━━━━━━━━━━━

Enter your complete name used during purchase.
""")
        return

    # First Approve
    if data.startswith("approve_"):
        target = int(data.split("_")[1])
        update(target, "status", "payment_pending")

        await q.edit_message_reply_markup(None)  # remove buttons only

        keyboard = [
            [InlineKeyboardButton("💰 Binance", callback_data=f"pay_binance_{target}")],
            [InlineKeyboardButton("📱 Easypaisa", callback_data=f"pay_easypaisa_{target}")]
        ]

        await context.bot.send_message(target, f"""
━━━━━━━━━━━━━━━━━━━━━━
🎉 APPLICATION APPROVED
━━━━━━━━━━━━━━━━━━━━━━

Your request has been approved.

To activate Premium Membership, complete the lifetime fee.

💎 Membership Fee: {MEMBERSHIP_FEE}

Select payment method below:
""", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Payment method selected
    if data.startswith("pay_"):
        target = int(data.split("_")[2])
        method = "Binance" if "binance" in data else "Easypaisa"
        update(target, "payment_method", method)

        details = f"""
━━━━━━━━━━━━━━━━━━━━━━
💳 PAYMENT DETAILS
━━━━━━━━━━━━━━━━━━━━━━

Method: {method}
Amount: {MEMBERSHIP_FEE}
"""

        if method == "Binance":
            details += f"\nEmail: {BINANCE_EMAIL}\nNetwork: {BINANCE_NETWORK}"
        else:
            details += f"\nAccount: {EASYPAYSA_NUMBER}"

        details += "\n\nAfter payment, upload payment screenshot."

        await context.bot.send_message(target, details)
        return

    # Final Verify
    if data.startswith("final_"):
        target = int(data.split("_")[1])
        update(target, "status", "completed")

        await q.edit_message_reply_markup(None)

        await context.bot.send_message(target, f"""
━━━━━━━━━━━━━━━━━━━━━━
🏆 PREMIUM MEMBERSHIP ACTIVATED
━━━━━━━━━━━━━━━━━━━━━━

Congratulations!

Telegram:
{TELEGRAM_GROUP_LINK}

WhatsApp:
{WHATSAPP_GROUP_LINK}

Welcome to the Inner Circle.
""", parse_mode=ParseMode.MARKDOWN)
        return

# ================= TEXT =================

async def text(update: Update, context):
    user = get_user(update.effective_user.id)
    if not user:
        return

    step = user[9]

    if step == "name":
        update(user[0], "full_name", update.message.text)
        update(user[0], "step", "email")
        await update.message.reply_text("""
━━━━━━━━━━━━━━━━━━━━━━
STEP 2 OF 4 — EMAIL CONFIRMATION
━━━━━━━━━━━━━━━━━━━━━━
Enter your registered email.
""")
        return

    if step == "email":
        update(user[0], "email", update.message.text)
        update(user[0], "step", "proof")
        await update.message.reply_text("""
━━━━━━━━━━━━━━━━━━━━━━
STEP 3 OF 4 — PURCHASE PROOF
━━━━━━━━━━━━━━━━━━━━━━
Upload your purchase screenshot.
""")
        return

    if step == "whatsapp":
        update(user[0], "whatsapp", update.message.text)
        update(user[0], "step", "done")

        await update.message.reply_text("""
━━━━━━━━━━━━━━━━━━━━━━
✅ APPLICATION SUBMITTED
━━━━━━━━━━━━━━━━━━━━━━

Your information has been forwarded for admin review.
""")

# ================= PHOTO =================

async def photo(update: Update, context):
    user = get_user(update.effective_user.id)
    if not user:
        return

    # Purchase proof
    if user[9] == "proof":
        update(user[0], "proof", update.message.photo[-1].file_id)
        update(user[0], "step", "whatsapp")
        await update.message.reply_text("""
━━━━━━━━━━━━━━━━━━━━━━
STEP 4 OF 4 — WHATSAPP NUMBER
━━━━━━━━━━━━━━━━━━━━━━
Enter your WhatsApp number with country code.
""")
        return

    # Payment proof
    if user[10] == "payment_pending":
        update(user[0], "payment_proof", update.message.photo[-1].file_id)

        keyboard = [[InlineKeyboardButton("✅ VERIFY & ACTIVATE",
                                          callback_data=f"final_{user[0]}")]]

        await context.bot.send_photo(
            ADMIN_ID,
            update.message.photo[-1].file_id,
            caption=f"""
💰 PAYMENT RECEIVED

User: @{user[1]}
Name: {user[2]}
Email: {user[3]}
WhatsApp: {user[4]}
Method: {user[8]}
""",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        await update.message.reply_text("""
⏳ Payment submitted successfully.
Admin team will review within 24 hours.
""")
        return

# ================= MAIN =================

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))
    app.add_handler(MessageHandler(filters.PHOTO, photo))
    app.run_polling()

if __name__ == "__main__":
    main()
