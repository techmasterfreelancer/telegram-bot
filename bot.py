import logging
import sqlite3
import hashlib
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from telegram.constants import ParseMode

# ================= CONFIG =================

BOT_TOKEN = "8535390425:AAH4RF9v6k8H6fMQeXr_OQ6JuB7PV8gvgLs"
ADMIN_ID = 7291034213

TELEGRAM_GROUP_LINK = "https://t.me/yourlink"
WHATSAPP_GROUP_LINK = "https://chat.whatsapp.com/yourlink"

MEMBERSHIP_FEE = "$5 USD (Lifetime)"

# ==========================================

logging.basicConfig(level=logging.INFO)
DB = "premium.db"


# ================= DATABASE =================

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            email TEXT,
            whatsapp TEXT,
            status TEXT DEFAULT 'new',
            step TEXT DEFAULT 'start',
            created TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()


def db():
    return sqlite3.connect(DB)


def get_user(user_id):
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    r = c.fetchone()
    conn.close()
    return r


def update(user_id, field, value):
    conn = db()
    c = conn.cursor()
    c.execute(f"UPDATE users SET {field}=? WHERE user_id=?", (value, user_id))
    conn.commit()
    conn.close()


def create_user(user_id):
    conn = db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, created) VALUES (?,?)", (user_id, datetime.now()))
    conn.commit()
    conn.close()


# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    create_user(user.id)

    keyboard = [
        [InlineKeyboardButton("💎 Join Premium", callback_data="join")]
    ]

    await update.message.reply_text(
        f"""
🎯 *WELCOME TO TECH MASTER PREMIUM*

Hello {user.first_name} 👋

You are one step away from joining our Exclusive Premium Community.

📚 Weekly Live Sessions  
📢 Instant Updates  
🛠 Full Support  
🏆 Lifetime Access  

Click below to begin verification.
""",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )


# ================= CALLBACK =================

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    # START JOIN FLOW
    if data == "join":
        update(user_id, "step", "name")
        await query.edit_message_text(
            "📝 *Step 1/3*\n\nEnter your *Full Name:*",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # ADMIN APPROVE
    if data.startswith("approve_"):
        target = int(data.split("_")[1])
        target_data = get_user(target)

        if not target_data or target_data[4] != "pending":
            await query.answer("Already processed!", show_alert=True)
            return

        update(target, "status", "approved")

        await query.edit_message_reply_markup(None)

        await context.bot.send_message(
            chat_id=target,
            text=f"""
🎉 *APPLICATION APPROVED*

Please send payment of {MEMBERSHIP_FEE}

After payment send screenshot here.
""",
            parse_mode=ParseMode.MARKDOWN
        )

        await query.message.reply_text("✅ User Approved")
        return

    # ADMIN REJECT
    if data.startswith("reject_"):
        target = int(data.split("_")[1])
        update(target, "status", "rejected")

        await query.edit_message_reply_markup(None)

        await context.bot.send_message(
            chat_id=target,
            text="❌ Your application has been rejected.",
        )

        await query.message.reply_text("❌ User Rejected")
        return


# ================= TEXT HANDLER =================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    user = get_user(user_id)

    if not user:
        return

    step = user[5]

    if step == "name":
        update(user_id, "full_name", text)
        update(user_id, "step", "email")

        await update.message.reply_text(
            "📧 *Step 2/3*\n\nEnter your Email:",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if step == "email":
        update(user_id, "email", text)
        update(user_id, "step", "whatsapp")

        await update.message.reply_text(
            "📱 *Step 3/3*\n\nEnter WhatsApp number with country code:\nExample: +923001234567",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if step == "whatsapp":
        update(user_id, "whatsapp", text)
        update(user_id, "status", "pending")
        update(user_id, "step", "done")

        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
            ]
        ]

        await update.message.reply_text(
            "✅ Application submitted. Waiting for admin approval."
        )

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"""
📥 *NEW PREMIUM REQUEST*

👤 Name: {user[1]}
📧 Email: {user[2]}
📱 WhatsApp: {text}
🆔 ID: {user_id}

Review below:
""",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )


# ================= MAIN =================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("🚀 Premium Bot Running...")
    app.run_polling()


if __name__ == "__main__":
    main()
