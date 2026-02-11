"""
Premium Support Bot - Final with Reject Warnings & Voice Support
"""

import logging
import sqlite3
import hashlib
import re
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Voice
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ============= CONFIGURATION =============

BOT_TOKEN = "8535390425:AAE-K_QBPRw7e23GoWnGzCISz7T6pjpBLjQ"
ADMIN_ID = 7291034213
TELEGRAM_GROUP_LINK = "https://t.me/+P8gZuIBH75RiOThk"
WHATSAPP_GROUP_LINK = "https://chat.whatsapp.com/YOUR_WHATSAPP_LINK_HERE"

# Payment Details
BINANCE_EMAIL = "techmasterfreelancer@gmail.com"
BINANCE_ID = "1129541950"
BINANCE_USDT_TRC20 = "TM6w24pqU7Z4FenAX4LfLHBCYB5x13XSvj"
EASYPAYSA_NAME = "Jaffar Ali"
EASYPAYSA_NUMBER = "03486623402"
MEMBERSHIP_FEE = "$5 USD (Lifetime)"

# Voice File IDs (Aap ne upload karne hain @BotFather se)
VOICE_MESSAGES = {
    'welcome': None,  # Yahan apne voice file_id dalna hai
    'name': None,
    'email': None,
    'proof': None,
    'whatsapp': None,
    'approved': None,
    'payment': None,
    'rejected': None,
    'warning_fake': None  # Fake info warning
}

# ========================================

logging.basicConfig(
    format='%(asctime)s │ %(name)s │ %(levelname)s │ %(message)s',
    level=logging.INFO,
    handlers=[logging.FileHandler('bot.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

DB_PATH = 'bot.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
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
            rejection_count INTEGER DEFAULT 0,
            warning_sent INTEGER DEFAULT 0,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS screenshots (
            id INTEGER PRIMARY KEY,
            file_hash TEXT UNIQUE,
            user_id INTEGER,
            used_at TIMESTAMP
        )
    ''')
    
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
    c.execute('''
        INSERT OR IGNORE INTO users 
        (user_id, username, current_step, status, created_at, updated_at) 
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, username, 'start', 'new', datetime.now(), datetime.now()))
    conn.commit()
    conn.close()

def update_user(user_id, field, value):
    conn = get_db()
    c = conn.cursor()
    c.execute(f"UPDATE users SET {field} = ?, updated_at = ? WHERE user_id = ?", 
              (value, datetime.now(), user_id))
    conn.commit()
    conn.close()

def save_hash(file_hash, user_id):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO screenshots (file_hash, user_id, used_at) VALUES (?, ?, ?)", 
                  (file_hash, user_id, datetime.now()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# ============= UI COMPONENTS =============

class PremiumUI:
    ICONS = {
        'crown': '👑', 'diamond': '💎', 'star': '⭐', 'sparkles': '✨',
        'fire': '🔥', 'rocket': '🚀', 'shield': '🛡️', 'vip': '🎖️',
        'money': '💵', 'money_bag': '💰', 'phone': '📱', 'email': '📧',
        'id': '🆔', 'check': '✅', 'cross': '❌', 'warning': '⚠️',
        'info': 'ℹ️', 'clock': '⏰', 'hourglass': '⏳', 'lock': '🔒',
        'unlock': '🔓', 'arrow': '➤', 'bullet': '•', 'trophy': '🏆',
        'gem': '💎', 'ban': '🚫', 'alert': '🚨', 'stop': '✋'
    }

# ============= WARNING MESSAGES =============

class WarningMessages:
    """Fake information warning system"""
    
    @staticmethod
    def fake_info_warning():
        return f"""
{PremiumUI.ICONS['alert']} {PremiumUI.ICONS['alert']} {PremiumUI.ICONS['alert']}

<b>⚠️ WARNING: FAKE INFORMATION DETECTED ⚠️</b>

{PremiumUI.ICONS['stop']} <b>This is your FIRST and FINAL warning!</b> {PremiumUI.ICONS['stop']}

You have submitted <b>fake or incorrect information</b>. This is a serious violation of our community rules.

{PremiumUI.ICONS['ban']} <b>CONSEQUENCES:</b>
• Immediate rejection of application
• Permanent ban from all services
• No future applications will be accepted
• Legal action may be taken for fraud

{PremiumUI.ICONS['info']} <b>If you believe this is a mistake:</b>
Contact admin with valid proof within 24 hours.

{PremiumUI.ICONS['alert']} {PremiumUI.ICONS['alert']} {PremiumUI.ICONS['alert']}
"""
    
    @staticmethod
    def final_ban_message():
        return f"""
{PremiumUI.ICONS['ban']} {PremiumUI.ICONS['ban']} {PremiumUI.ICONS['ban']}

<b>🚫 ACCOUNT BANNED PERMANENTLY 🚫</b>

You have been <b>PERMANENTLY BANNED</b> from our platform due to repeated fake information submission.

{PremiumUI.ICONS['cross']} <b>Actions Taken:</b>
• All data flagged in system
• IP address recorded
• Device information logged
• Reported to fraud prevention networks

{PremiumUI.ICONS['lock']} <b>This decision is FINAL and cannot be appealed.</b>

{PremiumUI.ICONS['ban']} {PremiumUI.ICONS['ban']} {PremiumUI.ICONS['ban']}
"""

# ============= MAIN BOT FUNCTIONS =============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    user_data = get_user(user_id)
    
    if not user_data:
        create_user(user_id, user.username or "No username")
        
        keyboard = [
            [InlineKeyboardButton("💎 Premium Subscription", callback_data='premium')],
            [InlineKeyboardButton("🛍️ Product Purchase", callback_data='product')]
        ]
        
        welcome_text = f"""
{PremiumUI.ICONS['crown']} <b>Welcome to Premium Access Bot</b> {PremiumUI.ICONS['crown']}

Hello <b>{user.first_name}</b>!

Select your membership type:
"""
        await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
        
        # Send voice if available
        if VOICE_MESSAGES['welcome']:
            await update.message.reply_voice(voice=VOICE_MESSAGES['welcome'])
        return
    
    # Check if banned
    if user_data[11] == 'banned':
        await update.message.reply_text(WarningMessages.final_ban_message(), parse_mode=ParseMode.HTML)
        return
    
    status = user_data[11]
    admin_approved = user_data[12]
    step = user_data[7]
    
    if status == 'completed':
        await update.message.reply_text(
            f"✅ You already have access!\n\n{TELEGRAM_GROUP_LINK}",
            disable_web_page_preview=True
        )
        return
    
    if admin_approved == 1 and status == 'payment_pending':
        keyboard = [
            [InlineKeyboardButton("💰 Binance Pay", callback_data='binance')],
            [InlineKeyboardButton("📱 Easypaisa", callback_data='easypaisa')]
        ]
        await update.message.reply_text(
            "✅ Approved! Please complete payment:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if step == 'info_submitted':
        await update.message.reply_text("⏳ Your application is under review...")
        return
    
    if step == 'payment_submitted':
        await update.message.reply_text("⏳ Payment verification in progress...")
        return
    
    # Resume steps
    if step == 'name_pending':
        await ask_name(update, context)
    elif step == 'email_pending':
        await ask_email(update, context, user_data[2])
    elif step == 'proof_pending':
        await ask_proof(update, context)
    elif step == 'whatsapp_pending':
        await ask_whatsapp(update, context)
    else:
        keyboard = [
            [InlineKeyboardButton("💎 Premium Subscription", callback_data='premium')],
            [InlineKeyboardButton("🛍️ Product Purchase", callback_data='product')]
        ]
        await update.message.reply_text("Welcome back! Select type:", reply_markup=InlineKeyboardMarkup(keyboard))

# ============= STEP FUNCTIONS WITH VOICE =============

async def ask_name(update, context, edit=False):
    text = f"""
{PremiumUI.ICONS['id']} <b>Step 1: Full Name</b>

Please enter your full name as per your ID:
"""
    if edit and hasattr(update, 'callback_query'):
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    
    # Send voice
    if VOICE_MESSAGES['name']:
        if edit and hasattr(update, 'callback_query'):
            await update.callback_query.message.reply_voice(voice=VOICE_MESSAGES['name'])
        else:
            await update.message.reply_voice(voice=VOICE_MESSAGES['name'])

async def ask_email(update, context, name, edit=False):
    text = f"""
{PremiumUI.ICONS['email']} <b>Step 2: Email Address</b>

Name: <b>{name}</b>

Please enter your email:
"""
    if edit:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    
    if VOICE_MESSAGES['email']:
        await update.message.reply_voice(voice=VOICE_MESSAGES['email'])

async def ask_proof(update, context, edit=False):
    text = f"""
{PremiumUI.ICONS['shield']} <b>Step 3: Purchase Proof</b>

Please upload a clear screenshot of your purchase:
"""
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    
    if VOICE_MESSAGES['proof']:
        await update.message.reply_voice(voice=VOICE_MESSAGES['proof'])

async def ask_whatsapp(update, context, edit=False):
    text = f"""
{PremiumUI.ICONS['phone']} <b>Step 4: WhatsApp Number</b>

Please enter your WhatsApp with country code:
<i>Example: +923001234567</i>
"""
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    
    if VOICE_MESSAGES['whatsapp']:
        await update.message.reply_voice(voice=VOICE_MESSAGES['whatsapp'])

# ============= CALLBACK HANDLER =============

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    if data in ['premium', 'product']:
        request_type = "Premium Subscription" if data == 'premium' else "Product Purchase"
        update_user(user_id, 'request_type', request_type)
        update_user(user_id, 'current_step', 'name_pending')
        
        await ask_name(update, context, edit=True)
        return
    
    if data in ['binance', 'easypaisa']:
        update_user(user_id, 'payment_method', data.capitalize())
        
        if data == 'binance':
            payment_text = f"""
💰 <b>Binance Payment Details</b>

Amount: <b>{MEMBERSHIP_FEE}</b>

USDT (TRC20): <code>{BINANCE_USDT_TRC20}</code>
Email: <code>{BINANCE_EMAIL}</code>
ID: <code>{BINANCE_ID}</code>

After payment, send screenshot here.
"""
        else:
            payment_text = f"""
📱 <b>Easypaisa Payment Details</b>

Amount: <b>Rs. 1,400</b> (Equivalent to $5 USD)

Name: <b>{EASYPAYSA_NAME}</b>
Number: <code>{EASYPAYSA_NUMBER}</code>

After payment, send screenshot here.
"""
        await query.edit_message_text(payment_text, parse_mode=ParseMode.HTML)
        return
    
    # Admin: Approve
    if data.startswith('approve_'):
        target_id = int(data.split('_')[1])
        
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE users SET admin_approved = 1, status = 'payment_pending', current_step = 'payment_pending' WHERE user_id = ?", (target_id,))
        conn.commit()
        conn.close()
        
        await query.edit_message_reply_markup(reply_markup=None)
        
        # Notify user
        keyboard = [
            [InlineKeyboardButton("💰 Binance Pay", callback_data='binance')],
            [InlineKeyboardButton("📱 Easypaisa", callback_data='easypaisa')]
        ]
        
        await context.bot.send_message(
            chat_id=target_id,
            text="✅ <b>Your application has been APPROVED!</b>\n\nPlease complete payment:",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Admin: Reject with WARNING
    if data.startswith('reject_'):
        target_id = int(data.split('_')[1])
        
        # Get user data to check rejection count
        user_data = get_user(target_id)
        rejection_count = user_data[13] if user_data[13] else 0
        warning_sent = user_data[14] if user_data[14] else 0
        
        conn = get_db()
        c = conn.cursor()
        
        if rejection_count == 0 and warning_sent == 0:
            # First rejection - Send WARNING
            c.execute("UPDATE users SET rejection_count = 1, warning_sent = 1 WHERE user_id = ?", (target_id,))
            conn.commit()
            conn.close()
            
            # Send warning to user
            await context.bot.send_message(
                chat_id=target_id,
                text=WarningMessages.fake_info_warning(),
                parse_mode=ParseMode.HTML
            )
            
            # Send voice warning if available
            if VOICE_MESSAGES['warning_fake']:
                await context.bot.send_voice(chat_id=target_id, voice=VOICE_MESSAGES['warning_fake'])
            
            # Ask admin for reason
            context.user_data['warn_user_id'] = target_id
            
            await query.edit_message_reply_markup(reply_markup=None)
            await query.edit_message_caption(
                caption=query.message.caption + "\n\n⚠️ <b>FIRST WARNING SENT TO USER</b>\nUser has been warned. Application rejected.",
                parse_mode=ParseMode.HTML
            )
            
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"⚠️ User {target_id} has been WARNED for fake info.\n\nType rejection reason:"
            )
            
        else:
            # Second rejection - BAN permanently
            c.execute("UPDATE users SET status = 'banned', rejection_count = 2 WHERE user_id = ?", (target_id,))
            conn.commit()
            conn.close()
            
            # Ban user
            await context.bot.send_message(
                chat_id=target_id,
                text=WarningMessages.final_ban_message(),
                parse_mode=ParseMode.HTML
            )
            
            await query.edit_message_reply_markup(reply_markup=None)
            await query.edit_message_caption(
                caption=query.message.caption + "\n\n🚫 <b>USER BANNED PERMANENTLY</b>",
                parse_mode=ParseMode.HTML
            )
        return
    
    # Final approve
    if data.startswith('final_'):
        target_id = int(data.split('_')[1])
        
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE users SET status = 'completed' WHERE user_id = ?", (target_id,))
        conn.commit()
        conn.close()
        
        await query.edit_message_reply_markup(reply_markup=None)
        
        await context.bot.send_message(
            chat_id=target_id,
            text=f"🎉 <b>Payment Verified!</b>\n\n{TELEGRAM_GROUP_LINK}",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        return
    
    # Reject payment
    if data.startswith('rejectpay_'):
        target_id = int(data.split('_')[1])
        context.user_data['reject_payment_id'] = target_id
        
        await query.edit_message_reply_markup(reply_markup=None)
        
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"Payment rejection reason for user {target_id}:"
        )
        return

# ============= TEXT HANDLER =============

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    user_data = get_user(user_id)
    if not user_data:
        await update.message.reply_text("Please send /start")
        return
    
    # Check if banned
    if user_data[11] == 'banned':
        await update.message.reply_text(WarningMessages.final_ban_message(), parse_mode=ParseMode.HTML)
        return
    
    step = user_data[7]
    
    # Handle admin rejection reason
    if 'warn_user_id' in context.user_data:
        target_id = context.user_data['warn_user_id']
        await context.bot.send_message(
            chat_id=target_id,
            text=f"Reason: <i>{text}</i>",
            parse_mode=ParseMode.HTML
        )
        await update.message.reply_text(f"✅ Warning sent to user {target_id}")
        del context.user_data['warn_user_id']
        return
    
    if 'reject_payment_id' in context.user_data:
        target_id = context.user_data['reject_payment_id']
        await context.bot.send_message(
            chat_id=target_id,
            text=f"❌ <b>Payment Rejected</b>\n\nReason: <i>{text}</i>",
            parse_mode=ParseMode.HTML
        )
        await update.message.reply_text(f"✅ Payment rejection sent to user {target_id}")
        del context.user_data['reject_payment_id']
        return
    
    # Name
    if step == 'name_pending':
        if len(text) < 2:
            await update.message.reply_text("❌ Name too short. Enter full name:")
            return
        
        update_user(user_id, 'full_name', text)
        update_user(user_id, 'current_step', 'email_pending')
        
        await ask_email(update, context, text)
        return
    
    # Email
    if step == 'email_pending':
        if "@" not in text or "." not in text.split('@')[-1]:
            await update.message.reply_text("❌ Invalid email. Try again:")
            return
        
        update_user(user_id, 'email', text)
        update_user(user_id, 'current_step', 'proof_pending')
        
        await ask_proof(update, context)
        return
    
    # WhatsApp
    if step == 'whatsapp_pending':
        clean = re.sub(r'[\s\-\(\)\.]', '', text)
        if not re.match(r'^\+\d{10,15}$', clean):
            await update.message.reply_text("❌ Invalid format. Use: +923001234567")
            return
        
        update_user(user_id, 'whatsapp', clean)
        update_user(user_id, 'current_step', 'info_submitted')
        
        await update.message.reply_text("✅ Application submitted! Under review...")
        
        # Send to admin
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f'approve_{user_id}'),
                InlineKeyboardButton("❌ Reject (Warning)", callback_data=f'reject_{user_id}')
            ]
        ]
        
        admin_text = f"""
🆕 <b>New Application</b>

User: @{user_data[1] or 'N/A'}
ID: <code>{user_id}</code>
Name: <b>{user_data[2]}</b>
Email: <b>{user_data[3]}</b>
WhatsApp: <code>{clean}</code>
Type: <b>{user_data[5]}</b>
"""
        
        if user_data[6]:
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=user_data[6],
                caption=admin_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return

# ============= PHOTO HANDLER =============

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    if not user_data:
        return
    
    # Check if banned
    if user_data[11] == 'banned':
        await update.message.reply_text(WarningMessages.final_ban_message(), parse_mode=ParseMode.HTML)
        return
    
    step = user_data[7]
    admin_approved = user_data[12]
    status = user_data[11]
    
    # First proof
    if step == 'proof_pending':
        file_id = update.message.photo[-1].file_id
        update_user(user_id, 'proof_file_id', file_id)
        update_user(user_id, 'current_step', 'whatsapp_pending')
        
        await ask_whatsapp(update, context)
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
            await update.message.reply_text("❌ Duplicate screenshot detected!")
            conn.close()
            return
        
        c.execute("INSERT INTO screenshots (file_hash, user_id, used_at) VALUES (?, ?, ?)", 
                  (hash_val, user_id, datetime.now()))
        c.execute("""
            UPDATE users 
            SET payment_file_id = ?, payment_hash = ?, current_step = 'payment_submitted', status = 'payment_verification' 
            WHERE user_id = ?
        """, (photo.file_id, hash_val, user_id))
        conn.commit()
        conn.close()
        
        await update.message.reply_text("⏳ Payment received! Verifying...")
        
        # Send to admin
        keyboard = [
            [
                InlineKeyboardButton("✅ Verify & Grant Access", callback_data=f'final_{user_id}'),
                InlineKeyboardButton("❌ Reject Payment", callback_data=f'rejectpay_{user_id}')
            ]
        ]
        
        admin_text = f"""
💰 <b>Payment Verification Required</b>

User: @{user_data[1] or 'N/A'}
ID: <code>{user_id}</code>
Name: <b>{user_data[2]}</b>
Method: <b>{user_data[8]}</b>
"""
        
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo.file_id,
            caption=admin_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("🤖 Bot started with Reject Warning System!")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()
