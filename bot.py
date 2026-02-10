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
        step TEXT DEFAULT 'start',
        status TEXT DEFAULT 'new'
    )""")
    conn.commit()
    conn.close()

init_db()

def db():
    return sqlite3.connect(DB)

def get_user(uid):
    conn=db(); c=conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    r=c.fetchone(); conn.close(); return r

def update(uid, field, value):
    conn=db(); c=conn.cursor()
    c.execute(f"UPDATE users SET {field}=? WHERE user_id=?", (value,uid))
    conn.commit(); conn.close()

def create(uid, username):
    conn=db(); c=conn.cursor()
    c.execute("INSERT OR IGNORE INTO users(user_id,username) VALUES(?,?)",(uid,username))
    conn.commit(); conn.close()

# ================= PREMIUM MESSAGES =================

WELCOME = """
━━━━━━━━━━━━━━━━━━━━━━
🎓 PREMIUM ACCESS PORTAL
━━━━━━━━━━━━━━━━━━━━━━

Welcome {name},

To maintain community quality,
all members go through verification.

Select your purchase type below.
"""

SUBMITTED_MSG = """
🎉 Application Submitted Successfully!

━━━━━━━━━━━━━━━━━━━━━━
✅ What happens next?
━━━━━━━━━━━━━━━━━━━━━━

Step 1: Admin reviews your application  
Estimated time: 2–24 hours  

Step 2: You'll receive approval notification  

Step 3: Complete payment  

Step 4: Get instant premium access  

━━━━━━━━━━━━━━━━━━━━━━
📊 Status: PENDING REVIEW
━━━━━━━━━━━━━━━━━━━━━━

Please do not submit multiple requests.
"""

PAYMENT_REVIEW = """
━━━━━━━━━━━━━━━━━━━━━━
⏳ PAYMENT SUBMITTED
━━━━━━━━━━━━━━━━━━━━━━

Your payment proof has been sent to admin.

Verification time: up to 24 hours.

Please wait for confirmation.
"""

FINAL_SUCCESS = """
━━━━━━━━━━━━━━━━━━━━━━
🏆 PREMIUM ACCESS GRANTED
━━━━━━━━━━━━━━━━━━━━━━

Congratulations!

Your payment has been verified.

🔗 Telegram Group:
{tg}

🔗 WhatsApp Community:
{wa}

Welcome to the Premium Circle.
"""

# ================= BOT =================

async def start(update:Update,context):
    user=update.effective_user
    if not get_user(user.id):
        create(user.id,user.username or "NoUsername")

    kb=[
        [InlineKeyboardButton("💎 Premium Subscription",callback_data="type_premium")],
        [InlineKeyboardButton("🛒 Product Purchase",callback_data="type_product")]
    ]
    await update.message.reply_text(WELCOME.format(name=user.first_name),
                                    reply_markup=InlineKeyboardMarkup(kb))

async def callback(update:Update,context):
    q=update.callback_query
    await q.answer()
    uid=q.from_user.id

    if q.data.startswith("type_"):
        t="Premium Subscription" if "premium" in q.data else "Product Purchase"
        update(uid,"request_type",t)
        update(uid,"step","name")
        await q.edit_message_text("Enter Full Name:")
        return

    if q.data.startswith("approve_"):
        target=int(q.data.split("_")[1])
        update(target,"status","billing")

        kb=[
            [InlineKeyboardButton("💰 Pay with Binance",callback_data="pay_binance")],
            [InlineKeyboardButton("📱 Pay with Easypaisa",callback_data="pay_easypaisa")]
        ]
        await context.bot.send_message(
            chat_id=target,
            text=f"Your application is APPROVED.\n\nMembership Fee: {MEMBERSHIP_FEE}",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        await q.edit_message_reply_markup(None)
        return

    if q.data.startswith("reject_"):
        target=int(q.data.split("_")[1])
        update(target,"status","rejected")
        await context.bot.send_message(
            chat_id=target,
            text="Your application has been rejected due to invalid or fake information."
        )
        await q.edit_message_reply_markup(None)
        return

    if q.data.startswith("final_"):
        target=int(q.data.split("_")[1])
        update(target,"status","completed")
        await context.bot.send_message(
            chat_id=target,
            text=FINAL_SUCCESS.format(tg=TELEGRAM_GROUP_LINK,wa=WHATSAPP_GROUP_LINK)
        )
        await q.edit_message_reply_markup(None)
        return

async def text(update:Update,context):
    uid=update.effective_user.id
    u=get_user(uid)
    if not u: return

    step=u[8]

    if step=="name":
        update(uid,"full_name",update.message.text)
        update(uid,"step","email")
        await update.message.reply_text("Enter Email:")
        return

    if step=="email":
        update(uid,"email",update.message.text)
        update(uid,"step","proof")
        await update.message.reply_text("Upload Purchase Screenshot:")
        return

    if step=="whatsapp":
        update(uid,"whatsapp",update.message.text)
        update(uid,"step","submitted")
        await update.message.reply_text(SUBMITTED_MSG)

        fresh=get_user(uid)

        kb=[[InlineKeyboardButton("✅ APPROVE",callback_data=f"approve_{uid}"),
             InlineKeyboardButton("❌ REJECT",callback_data=f"reject_{uid}")]]
        
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=fresh[6],
            caption=f"""
🚨 NEW APPLICATION

User: @{fresh[1]}
ID: {uid}
Name: {fresh[2]}
Email: {fresh[3]}
WhatsApp: {fresh[4]}
Type: {fresh[5]}
""",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return

async def photo(update:Update,context):
    uid=update.effective_user.id
    u=get_user(uid)
    if not u: return

    if u[8]=="proof":
        update(uid,"proof_file",update.message.photo[-1].file_id)
        update(uid,"step","whatsapp")
        await update.message.reply_text("Enter WhatsApp Number (+923...)")
        return

    if u[9]=="billing":
        update(uid,"payment_file",update.message.photo[-1].file_id)
        await update.message.reply_text(PAYMENT_REVIEW)

        kb=[[InlineKeyboardButton("✅ VERIFY & SEND LINKS",callback_data=f"final_{uid}")]]

        fresh=get_user(uid)

        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=fresh[7],
            caption=f"""
💰 PAYMENT RECEIVED

User: @{fresh[1]}
Name: {fresh[2]}
Email: {fresh[3]}
WhatsApp: {fresh[4]}
""",
            reply_markup=InlineKeyboardMarkup(kb)
        )

def main():
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,text))
    app.add_handler(MessageHandler(filters.PHOTO,photo))
    print("Premium Bot Running...")
    app.run_polling()

if __name__=="__main__":
    main()
