import logging
import sqlite3
import hashlib
import re
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ConversationHandler, ContextTypes, filters
from telegram.constants import ParseMode

# ============= CONFIGURATION =============
# Railway pe Environment Variables se lenge, nahi toh yahan se

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8535390425:AAGdysiGhg5y82rCLkVi2t2yJGGhCXXlnIY')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '7291034213'))
TELEGRAM_GROUP_LINK = os.environ.get('TELEGRAM_GROUP_LINK', 'https://t.me/+P8gZuIBH75RiOThk')
# PAYMENT DETAILS
BINANCE_EMAIL = os.environ.get('BINANCE_EMAIL', 'techmasterfreelancer@gmail.com')
BINANCE_ID = os.environ.get('BINANCE_ID', '1129541950')
BINANCE_NETWORK = os.environ.get('BINANCE_NETWORK', 'TRC20')
WALLET_ADDRESS = os.environ.get('TWzf9VJmr2mhq5H8Xa3bLhbb8dwmWdG9B7')

EASYPAYSA_NAME = os.environ.get('EASYPAYSA_NAME', 'Jaffar Ali')
EASYPAYSA_NUMBER = os.environ.get('EASYPAYSA_NUMBER', '03486623402')

MEMBERSHIP_FEE = os.environ.get('MEMBERSHIP_FEE', '$5 USD (Lifetime)')

# ========================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============= DATABASE =============

DB_PATH = 'bot.db'

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
    
    c.execute('''CREATE TABLE IF NOT EXISTS screenshots (
        id INTEGER PRIMARY KEY,
        file_hash TEXT UNIQUE,
        user_id INTEGER,
        used_at TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()

init_db()

def get_db():
    return sqlite3.connect(DB_PATH)

def get_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result

def create_user(user_id, username):
    conn = get_db()
    c = conn.cursor()
    now = datetime.now()
    c.execute('''INSERT OR IGNORE INTO users 
                 (user_id, username, current_step, status, created_at, updated_at) 
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (user_id, username, 'start', 'new', now, now))
    conn.commit()
    conn.close()

def update_user(user_id, field, value):
    conn = get_db()
    c = conn.cursor()
    c.execute(f"UPDATE users SET {field} = ?, updated_at = ? WHERE user_id = ?",
              (value, datetime.now(), user_id))
    conn.commit()
    conn.close()

def check_duplicate(file_hash):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT user_id FROM screenshots WHERE file_hash = ?", (file_hash,))
    result = c.fetchone()
    conn.close()
    return result

def save_hash(file_hash, user_id):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO screenshots (file_hash, user_id, used_at) VALUES (?, ?, ?)",
                  (file_hash, user_id, datetime.now()))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

# ============= STATES =============

SELECT_TYPE, GET_NAME, GET_EMAIL, GET_PROOF, GET_WHATSAPP, ADMIN_REVIEW, SELECT_PAYMENT, GET_PAYMENT_PROOF = range(8)

# ============= START =============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or "No username"
    first_name = user.first_name
    
    user_data = get_user(user_id)
    
    if not user_data:
        create_user(user_id, username)
        await send_welcome(update, first_name)
        return SELECT_TYPE
    
    step = user_data[7]
    status = user_data[11]
    admin_approved = user_data[12]
    
    if status == 'completed':
        await update.message.reply_text(
            f"✅ Welcome back {first_name}!\n\nYou already have access.\n\n"
            f"🔗 Telegram: {TELEGRAM_GROUP_LINK}\n"
            f"📱 WhatsApp: {WHATSAPP_GROUP_LINK}",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    if admin_approved == 1 and status == 'payment_pending':
        keyboard = [
            [InlineKeyboardButton("💰 Binance", callback_data='pay_binance')],
            [InlineKeyboardButton("📱 Easypaisa", callback_data='pay_easypaisa')]
        ]
        await update.message.reply_text(
            f"⏰ Payment Reminder for {first_name}\n\n"
            f"✅ Your application is APPROVED!\n\n"
            f"💎 Fee: {MEMBERSHIP_FEE}\n\n"
            f"👇 Select payment method:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        return SELECT_PAYMENT
    
    if step == 'info_submitted' and admin_approved == 0:
        await update.message.reply_text(
            f"⏳ Hello {first_name}!\n\n"
            f"Your information is submitted.\n"
            f"Status: PENDING\n\n"
            f"Please wait for admin review.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    if step == 'payment_submitted':
        await update.message.reply_text(
            f"⏳ Hello {first_name}!\n\n"
            f"Your payment proof is under verification.\n"
            f"Please wait...",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    if step == 'name_pending':
        await update.message.reply_text(
            f"🔄 Welcome back {first_name}!\n\nEnter your full name:",
            parse_mode=ParseMode.MARKDOWN
        )
        return GET_NAME
    
    if step == 'email_pending':
        await update.message.reply_text(
            f"🔄 Welcome back!\n\n✅ Name: {user_data[2]}\n\nEnter your email:",
            parse_mode=ParseMode.MARKDOWN
        )
        return GET_EMAIL
    
    if step == 'proof_pending':
        await update.message.reply_text(
            f"🔄 Welcome back!\n\nPlease send your proof screenshot:",
            parse_mode=ParseMode.MARKDOWN
        )
        return GET_PROOF
    
    if step == 'whatsapp_pending':
        await update.message.reply_text(
            f"🔄 Welcome back!\n\nEnter your WhatsApp number:",
            parse_mode=ParseMode.MARKDOWN
        )
        return GET_WHATSAPP
    
    await send_welcome(update, first_name)
    return SELECT_TYPE

async def send_welcome(update, first_name):
    keyboard = [
        [InlineKeyboardButton("💎 Premium Subscription", callback_data='type_premium')],
        [InlineKeyboardButton("🛒 Product Purchase", callback_data='type_product')]
    ]
    await update.message.reply_text(
        f"👋 Welcome {first_name}!\n\nWhat did you buy from my website?\n\n👇 Please select:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

# ============= TYPE SELECTION =============

async def select_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data.split('_')[1]
    request_type = "Premium Subscription" if data == 'premium' else "Product Purchase"
    
    update_user(user_id, 'request_type', request_type)
    update_user(user_id, 'current_step', 'name_pending')
    
    await query.edit_message_text(
        f"✅ {request_type} selected!\n\n📝 Step 1/4: Enter your full name:",
        parse_mode=ParseMode.MARKDOWN
    )
    return GET_NAME

# ============= COLLECT INFO =============

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.message.text
    
    if len(name) < 2:
        await update.message.reply_text("❌ Name too short! Enter full name:")
        return GET_NAME
    
    update_user(user_id, 'full_name', name)
    update_user(user_id, 'current_step', 'email_pending')
    
    await update.message.reply_text(
        f"✅ Name: {name}\n\n📧 Step 2/4: Enter your email address:",
        parse_mode=ParseMode.MARKDOWN
    )
    return GET_EMAIL

async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    email = update.message.text.lower().strip()
    
    if "@" not in email or "." not in email:
        await update.message.reply_text("❌ Invalid email! Enter valid email:")
        return GET_EMAIL
    
    update_user(user_id, 'email', email)
    update_user(user_id, 'current_step', 'proof_pending')
    
    user_data = get_user(user_id)
    request_type = user_data[5] or "purchase"
    
    await update.message.reply_text(
        f"✅ Email: {email}\n\n📸 Step 3/4: Send your {request_type} proof (screenshot):",
        parse_mode=ParseMode.MARKDOWN
    )
    return GET_PROOF

async def get_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not update.message.photo:
        await update.message.reply_text("❌ Please send an image/screenshot!")
        return GET_PROOF
    
    photo = update.message.photo[-1]
    file_id = photo.file_id
    
    update_user(user_id, 'proof_file_id', file_id)
    update_user(user_id, 'current_step', 'whatsapp_pending')
    
    await update.message.reply_text(
        "✅ Proof received!\n\n📱 Step 4/4: Enter your WhatsApp number (with country code):\n\nExample: +923001234567",
        parse_mode=ParseMode.MARKDOWN
    )
    return GET_WHATSAPP

async def get_whatsapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    whatsapp = update.message.text.strip()
    
    clean_number = re.sub(r'[\s\-\(\)\.]', '', whatsapp)
    
    if not re.match(r'^\+\d{10,15}$', clean_number):
        await update.message.reply_text(
            "❌ Invalid WhatsApp number!\n\nEnter with country code:\n• +923001234567\n• +14155552671"
        )
        return GET_WHATSAPP
    
    update_user(user_id, 'whatsapp', clean_number)
    update_user(user_id, 'current_step', 'info_submitted')
    
    await update.message.reply_text(
        "✅ Your information has been successfully submitted!\n\n"
        "🕐 It has been sent to admin for review.\n\n"
        "Please wait... You will receive a notification once approved.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Send to admin
    user_data = get_user(user_id)
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f'approve_{user_id}'),
            InlineKeyboardButton("❌ Reject", callback_data=f'reject_{user_id}')
        ]
    ]
    
    caption = f"""
🆕 NEW APPLICATION FOR REVIEW

👤 User: @{user_data[1]}
🆔 ID: {user_id}
📋 Type: {user_data[5]}
📝 Name: {user_data[2]}
📧 Email: {user_data[3]}
📱 WhatsApp: {clean_number}
⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}

👇 Please review:
    """
    
    if user_data[6]:
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=user_data[6],
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    return ConversationHandler.END

# ============= ADMIN ACTIONS =============

async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        user_id = int(query.data.split('_')[1])
        
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE users SET admin_approved = 1, status = 'payment_pending', current_step = 'payment_pending', updated_at = ? WHERE user_id = ?",
                  (datetime.now(), user_id))
        conn.commit()
        conn.close()
        
        keyboard = [
            [InlineKeyboardButton("💰 Binance", callback_data='pay_binance')],
            [InlineKeyboardButton("📱 Easypaisa", callback_data='pay_easypaisa')]
        ]
        
        await context.bot.send_message(
            chat_id=user_id,
            text=f"""
🎉 CONGRATULATIONS! YOUR APPLICATION IS APPROVED!

✅ Admin has reviewed and approved your application!

💎 To join Premium Group, please pay the Lifetime Membership Fee:
💵 {MEMBERSHIP_FEE}

👇 Select your payment method:
            """,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        
        await query.edit_message_text(
            f"✅ Approved! User {user_id} has been notified to complete payment.",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error in admin_approve: {e}")
        await query.edit_message_text(f"Error: {e}")

async def admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        user_id = int(query.data.split('_')[1])
        context.user_data['reject_user_id'] = user_id
        
        await query.edit_message_text(
            f"❌ Rejecting user {user_id}\n\nPlease enter rejection reason:",
            parse_mode=ParseMode.MARKDOWN
        )
        return ADMIN_REVIEW
        
    except Exception as e:
        logger.error(f"Error in admin_reject: {e}")
        await query.edit_message_text(f"Error: {e}")

async def handle_rejection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reason = update.message.text
    user_id = context.user_data.get('reject_user_id')
    
    if not user_id:
        await update.message.reply_text("Error!")
        return ConversationHandler.END
    
    await context.bot.send_message(
        chat_id=user_id,
        text=f"""
❌ APPLICATION REJECTED

Your application has been rejected.

Reason: {reason}

You can apply again by sending /start
        """,
        parse_mode=ParseMode.MARKDOWN
    )
    
    await update.message.reply_text(f"❌ User {user_id} rejected.")
    return ConversationHandler.END

# ============= PAYMENT FLOW =============

async def show_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    method = query.data.split('_')[1]
    user_id = update.effective_user.id
    
    update_user(user_id, 'payment_method', method.capitalize())
    
    if method == 'binance':
        details = f"""
💰 BINANCE PAYMENT DETAILS

📧 Email: {BINANCE_EMAIL}
🆔 Binance ID: {BINANCE_ID}
🌐 Network: {BINANCE_NETWORK}

💵 Amount: {MEMBERSHIP_FEE}

✅ After payment, please send the screenshot here.
        """
    else:
        details = f"""
📱 EASYPAYSA PAYMENT DETAILS

👤 Account Name: {EASYPAYSA_NAME}
📞 Account Number: {EASYPAYSA_NUMBER}

💵 Amount: {MEMBERSHIP_FEE}

✅ After payment, please send the screenshot here.
        """
    
    await context.bot.send_message(
        chat_id=user_id,
        text=details,
        parse_mode=ParseMode.MARKDOWN
    )
    
    context.user_data[f'awaiting_payment_{user_id}'] = True

async def receive_payment_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    user_data = get_user(user_id)
    
    if not user_data:
        return
    
    status = user_data[11]
    admin_approved = user_data[12]
    
    if not (admin_approved == 1 and status == 'payment_pending'):
        return
    
    if not update.message.photo:
        await update.message.reply_text("❌ Please send payment screenshot as image!")
        return
    
    photo = update.message.photo[-1]
    photo_file = await photo.get_file()
    
    file_bytes = await photo_file.download_as_bytearray()
    image_hash = hashlib.md5(file_bytes).hexdigest()
    
    duplicate = check_duplicate(image_hash)
    if duplicate:
        await update.message.reply_text("🚫 THIS SCREENSHOT HAS ALREADY BEEN USED!")
        return
    
    save_hash(image_hash, user_id)
    
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET payment_file_id = ?, payment_hash = ?, current_step = ?, status = ? WHERE user_id = ?",
              (photo.file_id, image_hash, 'payment_submitted', 'payment_verification', user_id))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        "⏳ Payment Screenshot Received!\n\n"
        "✅ Admin is verifying your payment...\n"
        "🕐 You will receive group links once verified.\n\n"
        "⚠️ Fake screenshots will result in permanent ban!",
        parse_mode=ParseMode.MARKDOWN
    )
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve & Send Links", callback_data=f'approvelink_{user_id}'),
            InlineKeyboardButton("❌ Reject Payment", callback_data=f'rejectpay_{user_id}')
        ]
    ]
    
    caption = f"""
💰 NEW PAYMENT RECEIVED FOR VERIFICATION

👤 User: @{user_data[1]}
🆔 ID: {user_id}
📝 Name: {user_data[2]}
📧 Email: {user_data[3]}
📱 WhatsApp: {user_data[4]}
💳 Payment Method: {user_data[8] or 'Not specified'}
⏰ Received: {datetime.now().strftime('%Y-%m-%d %H:%M')}

👇 Please verify and take action:
    """
    
    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo.file_id,
        caption=caption,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def final_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        user_id = int(query.data.split('_')[1])
        
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE users SET status = 'completed', current_step = 'completed', updated_at = ? WHERE user_id = ?",
                  (datetime.now(), user_id))
        conn.commit()
        conn.close()
        
        await context.bot.send_message(
            chat_id=user_id,
            text=f"""
🎉 PAYMENT VERIFIED SUCCESSFULLY!

✅ Your payment has been verified!

🔗 TELEGRAM PREMIUM GROUP:
{TELEGRAM_GROUP_LINK}

📱 WHATSAPP PREMIUM GROUP:
{WHATSAPP_GROUP_LINK}

⚠️ Important Rules:
• Do not share these links with anyone
• Follow all group rules
• Do not add fake members
• Lifetime access granted

🚀 Welcome to Premium Family! Enjoy your access!
            """,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=False
        )
        
        await query.edit_message_text(
            f"✅ User {user_id} fully approved!\nBoth group links sent.",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error in final_approve: {e}")
        await query.edit_message_text(f"Error: {e}")

async def reject_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        user_id = int(query.data.split('_')[1])
        context.user_data['reject_user_id'] = user_id
        
        await query.edit_message_text(
            f"❌ Rejecting payment from user {user_id}\n\nPlease enter rejection reason:",
            parse_mode=ParseMode.MARKDOWN
        )
        return ADMIN_REVIEW
        
    except Exception as e:
        logger.error(f"Error in reject_payment: {e}")
        await query.edit_message_text(f"Error: {e}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled.\nSend /start to begin again.")
    return ConversationHandler.END

# ============= MAIN =============

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECT_TYPE: [CallbackQueryHandler(select_type, pattern='^type_')],
            GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            GET_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
            GET_PROOF: [MessageHandler(filters.PHOTO, get_proof)],
            GET_WHATSAPP: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_whatsapp)],
            ADMIN_REVIEW: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_rejection)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(conv_handler)
    
    # Admin callbacks - FIXED PATTERNS
    application.add_handler(CallbackQueryHandler(admin_approve, pattern='^approve_\\d+$'))
    application.add_handler(CallbackQueryHandler(admin_reject, pattern='^reject_\\d+$'))
    application.add_handler(CallbackQueryHandler(show_payment_details, pattern='^pay_'))
    application.add_handler(CallbackQueryHandler(final_approve, pattern='^approvelink_\\d+$'))
    application.add_handler(CallbackQueryHandler(reject_payment, pattern='^rejectpay_\\d+$'))
    
    # Payment proof handler
    application.add_handler(MessageHandler(filters.PHOTO, receive_payment_proof))
    
    logger.info("Bot started successfully!")
    application.run_polling()

if __name__ == '__main__':
    main()
