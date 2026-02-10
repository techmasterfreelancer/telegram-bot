import logging
import sqlite3
import hashlib
import re
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.constants import ParseMode

# ============= YOUR SETTINGS =============

BOT_TOKEN = "8535390425:AAFLbRWHfy9reLO94h91N5wlAou4gxfgK3c"
ADMIN_ID = 7291034213
TELEGRAM_GROUP_LINK = "https://t.me/+YOUR_LINK"
WHATSAPP_GROUP_LINK = "https://chat.whatsapp.com/YOUR_LINK"

BINANCE_EMAIL = "your.binance@email.com"
BINANCE_ID = "123456789"
EASYPAYSA_NAME = "Your Name"
EASYPAYSA_NUMBER = "03XX-XXXXXXX"
MEMBERSHIP_FEE = "$5 USD (Lifetime)"

# ========================================

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Database
DB_PATH = 'bot.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, email TEXT,
        whatsapp TEXT, request_type TEXT, proof_file_id TEXT, current_step TEXT DEFAULT 'start',
        payment_method TEXT, payment_file_id TEXT, payment_hash TEXT UNIQUE,
        status TEXT DEFAULT 'new', admin_approved INTEGER DEFAULT 0,
        created_at TIMESTAMP, updated_at TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS screenshots (id INTEGER PRIMARY KEY, file_hash TEXT UNIQUE, user_id INTEGER, used_at TIMESTAMP)''')
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
    c.execute('INSERT OR IGNORE INTO users (user_id, username, current_step, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)',
              (user_id, username, 'start', 'new', datetime.now(), datetime.now()))
    conn.commit()
    conn.close()

def update_user(user_id, field, value):
    conn = get_db()
    c = conn.cursor()
    c.execute(f"UPDATE users SET {field} = ?, updated_at = ? WHERE user_id = ?", (value, datetime.now(), user_id))
    conn.commit()
    conn.close()

def save_hash(file_hash, user_id):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO screenshots (file_hash, user_id, used_at) VALUES (?, ?, ?)", (file_hash, user_id, datetime.now()))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

# ============= BOT FUNCTIONS =============

async def start(update: Update, context):
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name
    
    user_data = get_user(user_id)
    
    if not user_data:
        create_user(user_id, user.username or "No username")
        keyboard = [[InlineKeyboardButton("💎 Premium Subscription", callback_data='premium')],
                    [InlineKeyboardButton("🛒 Product Purchase", callback_data='product')]]
        await update.message.reply_text(f"👋 Welcome {first_name}!\n\nWhat did you buy?", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # Check status and respond accordingly
    status = user_data[11]
    admin_approved = user_data[12]
    step = user_data[7]
    
    if status == 'completed':
        await update.message.reply_text(f"✅ You already have access!\n\n🔗 Telegram: {TELEGRAM_GROUP_LINK}\n📱 WhatsApp: {WHATSAPP_GROUP_LINK}")
        return
    
    if admin_approved == 1 and status == 'payment_pending':
        keyboard = [[InlineKeyboardButton("💰 Binance", callback_data='binance')],
                    [InlineKeyboardButton("📱 Easypaisa", callback_data='easypaisa')]]
        await update.message.reply_text(f"⏰ Payment Reminder!\n\n✅ Approved! Pay {MEMBERSHIP_FEE}", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    if step == 'info_submitted':
        await update.message.reply_text("⏳ Your application is pending admin review.")
        return
    
    if step == 'payment_submitted':
        await update.message.reply_text("⏳ Your payment is being verified.")
        return
    
    # Resume
    if step == 'name_pending':
        await update.message.reply_text("🔄 Continue: Enter your full name:")
    elif step == 'email_pending':
        await update.message.reply_text(f"🔄 Continue: Name: {user_data[2]}\n\nEnter email:")
    elif step == 'proof_pending':
        await update.message.reply_text("🔄 Continue: Send proof screenshot:")
    elif step == 'whatsapp_pending':
        await update.message.reply_text("🔄 Continue: Enter WhatsApp number:")
    else:
        keyboard = [[InlineKeyboardButton("💎 Premium", callback_data='premium')],
                    [InlineKeyboardButton("🛒 Product", callback_data='product')]]
        await update.message.reply_text(f"👋 Welcome {first_name}!\n\nWhat did you buy?", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_callback(update: Update, context):
    """ALL callbacks handled here"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    logger.info(f"Callback received: {data} from user {user_id}")
    
    # STEP 1: Select type
    if data in ['premium', 'product']:
        request_type = "Premium Subscription" if data == 'premium' else "Product Purchase"
        update_user(user_id, 'request_type', request_type)
        update_user(user_id, 'current_step', 'name_pending')
        await query.edit_message_text(f"✅ {request_type} selected!\n\n📝 Enter your full name:")
        return
    
    # STEP 2: Select payment method
    if data in ['binance', 'easypaisa']:
        update_user(user_id, 'payment_method', data.capitalize())
        
        if data == 'binance':
            text = f"💰 BINANCE PAYMENT\n\n📧 Email: {BINANCE_EMAIL}\n🆔 ID: {BINANCE_ID}\n💵 Amount: {MEMBERSHIP_FEE}\n\n✅ Send screenshot after payment:"
        else:
            text = f"📱 EASYPAYSA PAYMENT\n\n👤 Name: {EASYPAYSA_NAME}\n📞 Number: {EASYPAYSA_NUMBER}\n💵 Amount: {MEMBERSHIP_FEE}\n\n✅ Send screenshot after payment:"
        
        await query.edit_message_text(text)
        return
    
    # STEP 3: Admin approve first time
    if data.startswith('approve_'):
        try:
            target_id = int(data.split('_')[1])
            
            # Update user
            conn = get_db()
            c = conn.cursor()
            c.execute("UPDATE users SET admin_approved = 1, status = 'payment_pending', current_step = 'payment_pending' WHERE user_id = ?", (target_id,))
            conn.commit()
            conn.close()
            
            # Send payment request
            keyboard = [[InlineKeyboardButton("💰 Binance", callback_data='binance')],
                        [InlineKeyboardButton("📱 Easypaisa", callback_data='easypaisa')]]
            
            await context.bot.send_message(
                chat_id=target_id,
                text=f"🎉 APPROVED!\n\n💎 Pay {MEMBERSHIP_FEE} to join:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            await query.edit_message_text(f"✅ User {target_id} notified to pay.")
        except Exception as e:
            logger.error(f"Error in approve: {e}")
            await query.edit_message_text(f"Error: {e}")
        return
    
    # STEP 4: Admin reject first time
    if data.startswith('reject_'):
        try:
            target_id = int(data.split('_')[1])
            context.user_data['reject_id'] = target_id
            await query.edit_message_text(f"❌ Rejecting {target_id}\n\nEnter reason:")
        except Exception as e:
            logger.error(f"Error in reject: {e}")
            await query.edit_message_text(f"Error: {e}")
        return
    
    # STEP 5: FINAL APPROVE - Send links
    if data.startswith('final_'):
        try:
            target_id = int(data.split('_')[1])
            
            conn = get_db()
            c = conn.cursor()
            c.execute("UPDATE users SET status = 'completed' WHERE user_id = ?", (target_id,))
            conn.commit()
            conn.close()
            
            # Send links
            await context.bot.send_message(
                chat_id=target_id,
                text=f"🎉 VERIFIED!\n\n🔗 Telegram: {TELEGRAM_GROUP_LINK}\n📱 WhatsApp: {WHATSAPP_GROUP_LINK}"
            )
            
            await query.edit_message_text(f"✅ User {target_id} approved - Links sent!")
        except Exception as e:
            logger.error(f"Error in final: {e}")
            await query.edit_message_text(f"Error: {e}")
        return
    
    # STEP 6: Reject payment
    if data.startswith('rejectpay_'):
        try:
            target_id = int(data.split('_')[1])
            context.user_data['reject_id'] = target_id
            await query.edit_message_text(f"❌ Reject payment {target_id}\n\nEnter reason:")
        except Exception as e:
            logger.error(f"Error in rejectpay: {e}")
            await query.edit_message_text(f"Error: {e}")
        return

async def handle_text(update: Update, context):
    """Handle all text messages"""
    user_id = update.effective_user.id
    text = update.message.text
    
    user_data = get_user(user_id)
    
    if not user_data:
        await update.message.reply_text("Send /start to begin")
        return
    
    step = user_data[7]
    
    # Name
    if step == 'name_pending':
        update_user(user_id, 'full_name', text)
        update_user(user_id, 'current_step', 'email_pending')
        await update.message.reply_text(f"✅ Name: {text}\n\n📧 Enter email:")
        return
    
    # Email
    if step == 'email_pending':
        if "@" not in text:
            await update.message.reply_text("❌ Invalid email! Try again:")
            return
        update_user(user_id, 'email', text)
        update_user(user_id, 'current_step', 'proof_pending')
        await update.message.reply_text(f"✅ Email: {text}\n\n📸 Send proof screenshot:")
        return
    
    # WhatsApp
    if step == 'whatsapp_pending':
        clean = re.sub(r'[\s\-\(\)\.]', '', text)
        if not re.match(r'^\+\d{10,15}$', clean):
            await update.message.reply_text("❌ Invalid! Use: +923001234567")
            return
        
        update_user(user_id, 'whatsapp', clean)
        update_user(user_id, 'current_step', 'info_submitted')
        
        await update.message.reply_text("✅ Submitted! Wait for admin review.")
        
        # Send to admin
        keyboard = [[InlineKeyboardButton("✅ Approve", callback_data=f'approve_{user_id}')],
                    [InlineKeyboardButton("❌ Reject", callback_data=f'reject_{user_id}')]]
        
        caption = f"🆕 NEW APPLICATION\n\n👤 User: @{user_data[1]}\n🆔 ID: {user_id}\n📝 Name: {user_data[2]}\n📧 Email: {user_data[3]}\n📱 WhatsApp: {clean}\n📋 Type: {user_data[5]}"
        
        if user_data[6]:  # proof
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=user_data[6], caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await context.bot.send_message(chat_id=ADMIN_ID, text=caption, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # Rejection reason
    if 'reject_id' in context.user_data:
        target_id = context.user_data['reject_id']
        await context.bot.send_message(chat_id=target_id, text=f"❌ REJECTED\n\nReason: {text}")
        await update.message.reply_text(f"❌ User {target_id} rejected.")
        del context.user_data['reject_id']
        return

async def handle_photo(update: Update, context):
    """Handle all photos"""
    user_id = update.effective_user.id
    
    user_data = get_user(user_id)
    if not user_data:
        return
    
    step = user_data[7]
    admin_approved = user_data[12]
    status = user_data[11]
    
    # First proof
    if step == 'proof_pending':
        file_id = update.message.photo[-1].file_id
        update_user(user_id, 'proof_file_id', file_id)
        update_user(user_id, 'current_step', 'whatsapp_pending')
        await update.message.reply_text("✅ Proof received!\n\n📱 Enter WhatsApp (+923001234567):")
        return
    
    # Payment proof
    if admin_approved == 1 and status == 'payment_pending':
        photo = update.message.photo[-1]
        
        # Check duplicate
        file = await photo.get_file()
        bytes_data = await file.download_as_bytearray()
        hash_val = hashlib.md5(bytes_data).hexdigest()
        
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT 1 FROM screenshots WHERE file_hash = ?", (hash_val,))
        if c.fetchone():
            await update.message.reply_text("🚫 DUPLICATE SCREENSHOT!")
            conn.close()
            return
        
        c.execute("INSERT INTO screenshots (file_hash, user_id, used_at) VALUES (?, ?, ?)", (hash_val, user_id, datetime.now()))
        c.execute("UPDATE users SET payment_file_id = ?, payment_hash = ?, current_step = 'payment_submitted', status = 'payment_verification' WHERE user_id = ?",
                  (photo.file_id, hash_val, user_id))
        conn.commit()
        conn.close()
        
        await update.message.reply_text("⏳ Payment received! Verifying...")
        
        # Send to admin with FINAL buttons
        keyboard = [[InlineKeyboardButton("✅ Approve & Send Links", callback_data=f'final_{user_id}')],
                    [InlineKeyboardButton("❌ Reject Payment", callback_data=f'rejectpay_{user_id}')]]
        
        caption = f"💰 PAYMENT VERIFY\n\n👤 User: @{user_data[1]}\n🆔 ID: {user_id}\n📝 {user_data[2]}\n💳 Method: {user_data[8]}"
        
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo.file_id, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))
        return

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))  # ALL callbacks
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("🤖 Bot started!")
    application.run_polling()

if __name__ == '__main__':
    main()
