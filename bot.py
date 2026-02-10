import logging
import sqlite3
import hashlib
import re
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.constants import ParseMode

# ============= YOUR DETAILS (PRE-FILLED) =============

BOT_TOKEN = "8535390425:AAH4RF9v6k8H6fMQeXr_OQ6JuB7PV8gvgLs"
ADMIN_ID = 7291034213
TELEGRAM_GROUP_LINK = "https://t.me/+P8gZuIBH75RiOThk"
WHATSAPP_GROUP_LINK = "https://chat.whatsapp.com/YOUR_WHATSAPP_LINK_HERE"

BINANCE_EMAIL = "techmasterfreelancer@gmail.com"
BINANCE_ID = "1129541950"
BINANCE_NETWORK = "TRC20"

EASYPAYSA_NAME = "Jaffar Ali"
EASYPAYSA_NUMBER = "03486623402"

MEMBERSHIP_FEE = "$5 USD (Lifetime)"

# ========================================

# Professional Logging Setup
logging.basicConfig(
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DB_PATH = 'bot.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Users table with enhanced fields
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
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            action_message_id INTEGER
        )
    ''')
    
    # Screenshots table for duplicate detection
    c.execute('''
        CREATE TABLE IF NOT EXISTS screenshots (
            id INTEGER PRIMARY KEY,
            file_hash TEXT UNIQUE,
            user_id INTEGER,
            used_at TIMESTAMP
        )
    ''')
    
    # Admin actions tracking table
    c.execute('''
        CREATE TABLE IF NOT EXISTS admin_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action_type TEXT,
            action_status TEXT,
            message_id INTEGER,
            chat_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

def track_admin_action(user_id, action_type, message_id, chat_id, status='pending'):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO admin_actions (user_id, action_type, action_status, message_id, chat_id)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, action_type, status, message_id, chat_id))
    conn.commit()
    conn.close()

def update_admin_action_status(user_id, action_type, new_status):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        UPDATE admin_actions 
        SET action_status = ? 
        WHERE user_id = ? AND action_type = ? AND action_status = 'pending'
    ''', (new_status, user_id, action_type))
    conn.commit()
    conn.close()

def get_pending_action_message(user_id, action_type):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT message_id, chat_id FROM admin_actions 
        WHERE user_id = ? AND action_type = ? AND action_status = 'pending'
    ''', (user_id, action_type))
    result = c.fetchone()
    conn.close()
    return result

# ============= UI COMPONENTS =============

class UI:
    """Professional UI Components"""
    
    # Color schemes and emojis
    ICONS = {
        'welcome': '👋',
        'premium': '💎',
        'product': '🛒',
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'info': 'ℹ️',
        'money': '💰',
        'phone': '📱',
        'email': '📧',
        'user': '👤',
        'id': '🆔',
        'time': '⏰',
        'wait': '⏳',
        'party': '🎉',
        'lock': '🔒',
        'link': '🔗',
        'rocket': '🚀',
        'star': '⭐',
        'check': '✓',
        'cross': '✗'
    }
    
    @staticmethod
    def header(text):
        return f"╔═══════════════════╗\n   {text}\n╚═══════════════════╝"
    
    @staticmethod
    def section(title, content):
        return f"\n┌─ {title} ─┐\n{content}\n└{'─' * (len(title) + 4)}┘"
    
    @staticmethod
    def status_badge(status):
        badges = {
            'new': '🔵 NEW',
            'pending': '🟡 PENDING',
            'approved': '🟢 APPROVED',
            'rejected': '🔴 REJECTED',
            'completed': '✅ COMPLETED',
            'payment_pending': '💳 PAYMENT PENDING',
            'payment_verification': '🔍 VERIFYING PAYMENT'
        }
        return badges.get(status, status.upper())
    
    @staticmethod
    def button(text, callback_data, style='primary'):
        styles = {
            'primary': '●',
            'success': '✓',
            'danger': '✗',
            'warning': '⚡'
        }
        prefix = styles.get(style, '●')
        return InlineKeyboardButton(f"{prefix} {text}", callback_data=callback_data)

# ============= BOT FUNCTIONS =============

async def start(update: Update, context):
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name
    
    user_data = get_user(user_id)
    
    # Welcome header
    welcome_text = f"""
{UI.ICONS['star']} <b>Welcome to Premium Access Bot</b> {UI.ICONS['star']}

Hello <b>{first_name}</b>! {UI.ICONS['welcome']}

This bot will guide you through the verification process 
to gain access to our exclusive Premium Groups.
"""
    
    if not user_data:
        create_user(user_id, user.username or "No username")
        
        keyboard = [
            [InlineKeyboardButton(f"{UI.ICONS['premium']} Premium Subscription", callback_data='premium')],
            [InlineKeyboardButton(f"{UI.ICONS['product']} Product Purchase", callback_data='product')]
        ]
        
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    status = user_data[11]
    admin_approved = user_data[12]
    step = user_data[7]
    
    # Already completed
    if status == 'completed':
        completed_text = f"""
{UI.ICONS['party']} <b>ACCESS GRANTED!</b> {UI.ICONS['party']}

{UI.ICONS['success']} You already have full access to our Premium Groups!

{UI.ICONS['link']} <b>Telegram Group:</b>
{TELEGRAM_GROUP_LINK}

{UI.ICONS['phone']} <b>WhatsApp Group:</b>
{WHATSAPP_GROUP_LINK}

{UI.ICONS['warning']} <i>Please do not share these links with anyone.</i>
"""
        await update.message.reply_text(completed_text, parse_mode=ParseMode.HTML)
        return
    
    # Approved, waiting for payment
    if admin_approved == 1 and status == 'payment_pending':
        payment_reminder = f"""
{UI.ICONS['success']} <b>APPLICATION APPROVED!</b>

Congratulations! Your application has been reviewed and approved.

{UI.ICONS['money']} <b>Payment Required:</b> {MEMBERSHIP_FEE}

Please select your preferred payment method below:
"""
        keyboard = [
            [InlineKeyboardButton(f"{UI.ICONS['money']} Binance Pay", callback_data='binance')],
            [InlineKeyboardButton(f"{UI.ICONS['phone']} Easypaisa", callback_data='easypaisa')]
        ]
        
        await update.message.reply_text(
            payment_reminder,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Pending review
    if step == 'info_submitted':
        await update.message.reply_text(
            f"{UI.ICONS['wait']} <b>Under Review</b>\n\n"
            f"Your application is currently being reviewed by our admin team.\n"
            f"Please be patient, you will be notified once approved.",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Payment verification pending
    if step == 'payment_submitted':
        await update.message.reply_text(
            f"{UI.ICONS['time']} <b>Payment Verification</b>\n\n"
            f"Your payment screenshot has been submitted and is being verified.\n"
            f"You will receive access links once confirmed.",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Resume incomplete steps
    if step == 'name_pending':
        await update.message.reply_text(
            f"{UI.ICONS['info']} <b>Continue Registration</b>\n\n"
            f"Please enter your <b>full name</b>:",
            parse_mode=ParseMode.HTML
        )
    elif step == 'email_pending':
        await update.message.reply_text(
            f"{UI.ICONS['info']} <b>Continue Registration</b>\n\n"
            f"Name: <b>{user_data[2]}</b>\n\n"
            f"Please enter your <b>email address</b>:",
            parse_mode=ParseMode.HTML
        )
    elif step == 'proof_pending':
        await update.message.reply_text(
            f"{UI.ICONS['info']} <b>Continue Registration</b>\n\n"
            f"Please send your <b>proof of purchase</b> screenshot:",
            parse_mode=ParseMode.HTML
        )
    elif step == 'whatsapp_pending':
        await update.message.reply_text(
            f"{UI.ICONS['info']} <b>Continue Registration</b>\n\n"
            f"Please enter your <b>WhatsApp number</b> (with country code):\n"
            f"<i>Example: +923001234567</i>",
            parse_mode=ParseMode.HTML
        )
    else:
        # Restart
        keyboard = [
            [InlineKeyboardButton(f"{UI.ICONS['premium']} Premium Subscription", callback_data='premium')],
            [InlineKeyboardButton(f"{UI.ICONS['product']} Product Purchase", callback_data='product')]
        ]
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_callback(update: Update, context):
    """Handle all callback queries with professional UI"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    logger.info(f"Callback received: {data} from user {user_id}")
    
    # Select subscription type
    if data in ['premium', 'product']:
        request_type = "Premium Subscription" if data == 'premium' else "Product Purchase"
        update_user(user_id, 'request_type', request_type)
        update_user(user_id, 'current_step', 'name_pending')
        
        selected_text = f"""
{UI.ICONS['success']} <b>{request_type}</b> selected!

{UI.ICONS['user']} Step 1 of 4: Personal Information

Please enter your <b>full name</b> (as on your ID):
"""
        await query.edit_message_text(selected_text, parse_mode=ParseMode.HTML)
        return
    
    # Select payment method
    if data in ['binance', 'easypaisa']:
        update_user(user_id, 'payment_method', data.capitalize())
        
        if data == 'binance':
            payment_text = f"""
{UI.ICONS['money']} <b>BINANCE PAYMENT DETAILS</b>

┌─ Transfer Information ─┐
{UI.ICONS['email']} Email: <code>{BINANCE_EMAIL}</code>
{UI.ICONS['id']} ID: <code>{BINANCE_ID}</code>
{UI.ICONS['link']} Network: <code>{BINANCE_NETWORK}</code>
{UI.ICONS['money']} Amount: <b>{MEMBERSHIP_FEE}</b>
└─────────────────────┘

{UI.ICONS['warning']} <i>Send exact amount to avoid delays</i>

{UI.ICONS['success']} After payment, send screenshot here for verification.
"""
        else:
            payment_text = f"""
{UI.ICONS['phone']} <b>EASYPAYSA PAYMENT DETAILS</b>

┌─ Transfer Information ─┐
{UI.ICONS['user']} Account Name: <b>{EASYPAYSA_NAME}</b>
{UI.ICONS['phone']} Number: <code>{EASYPAYSA_NUMBER}</code>
{UI.ICONS['money']} Amount: <b>{MEMBERSHIP_FEE}</b>
└─────────────────────┘

{UI.ICONS['warning']} <i>Send exact amount to avoid delays</i>

{UI.ICONS['success']} After payment, send screenshot here for verification.
"""
        
        await query.edit_message_text(payment_text, parse_mode=ParseMode.HTML)
        return
    
    # Admin: Approve initial application
    if data.startswith('approve_'):
        try:
            target_id = int(data.split('_')[1])
            
            conn = get_db()
            c = conn.cursor()
            c.execute("""
                UPDATE users 
                SET admin_approved = 1, status = 'payment_pending', current_step = 'payment_pending' 
                WHERE user_id = ?
            """, (target_id,))
            conn.commit()
            conn.close()
            
            # Remove buttons from admin message
            await query.edit_message_reply_markup(reply_markup=None)
            
            # Update message to show action taken
            original_text = query.message.text or query.message.caption or ""
            updated_text = f"{original_text}\n\n{UI.ICONS['success']} <b>ACTION TAKEN: APPROVED</b> ✅\n<i>User has been notified to complete payment.</i>"
            
            if query.message.photo:
                await query.edit_message_caption(caption=updated_text, parse_mode=ParseMode.HTML)
            else:
                await query.edit_message_text(updated_text, parse_mode=ParseMode.HTML)
            
            # Notify user
            keyboard = [
                [InlineKeyboardButton(f"{UI.ICONS['money']} Binance Pay", callback_data='binance')],
                [InlineKeyboardButton(f"{UI.ICONS['phone']} Easypaisa", callback_data='easypaisa')]
            ]
            
            await context.bot.send_message(
                chat_id=target_id,
                text=f"""
{UI.ICONS['party']} <b>CONGRATULATIONS!</b> {UI.ICONS['party']}

{UI.ICONS['success']} Your application has been <b>APPROVED</b>!

{UI.ICONS['money']} To complete your registration, please pay:
<b>{MEMBERSHIP_FEE}</b>

Select your payment method:
""",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            logger.info(f"Admin approved user {target_id}")
            
        except Exception as e:
            logger.error(f"Error in approve: {e}")
            await query.edit_message_text(f"{UI.ICONS['error']} Error: {e}")
        return
    
    # Admin: Reject initial application
    if data.startswith('reject_'):
        try:
            target_id = int(data.split('_')[1])
            context.user_data['reject_id'] = target_id
            
            # Remove buttons from admin message
            await query.edit_message_reply_markup(reply_markup=None)
            
            original_text = query.message.text or query.message.caption or ""
            updated_text = f"{original_text}\n\n{UI.ICONS['error']} <b>ACTION TAKEN: REJECTED</b> ❌\n<i>Waiting for rejection reason...</i>"
            
            if query.message.photo:
                await query.edit_message_caption(caption=updated_text, parse_mode=ParseMode.HTML)
            else:
                await query.edit_message_text(updated_text, parse_mode=ParseMode.HTML)
            
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"{UI.ICONS['error']} <b>Rejection Process</b>\n\nUser ID: <code>{target_id}</code>\n\nPlease type the reason for rejection:"
            )
            
        except Exception as e:
            logger.error(f"Error in reject: {e}")
            await query.edit_message_text(f"{UI.ICONS['error']} Error: {e}")
        return
    
    # Admin: Final approve after payment
    if data.startswith('final_'):
        try:
            target_id = int(data.split('_')[1])
            
            conn = get_db()
            c = conn.cursor()
            c.execute("UPDATE users SET status = 'completed' WHERE user_id = ?", (target_id,))
            conn.commit()
            conn.close()
            
            # Remove buttons from admin message
            await query.edit_message_reply_markup(reply_markup=None)
            
            # Update message to show action taken
            original_text = query.message.caption or ""
            updated_text = f"{original_text}\n\n{UI.ICONS['success']} <b>ACTION TAKEN: PAYMENT VERIFIED & LINKS SENT</b> ✅\n<i>User has been granted full access.</i>"
            
            await query.edit_message_caption(caption=updated_text, parse_mode=ParseMode.HTML)
            
            # Send access to user
            await context.bot.send_message(
                chat_id=target_id,
                text=f"""
{UI.ICONS['party']} <b>PAYMENT VERIFIED!</b> {UI.ICONS['party']}

{UI.ICONS['success']} Your payment has been confirmed!

{UI.ICONS['link']} <b>TELEGRAM GROUP:</b>
{TELEGRAM_GROUP_LINK}

{UI.ICONS['phone']} <b>WhatsApp Group:</b>
{WHATSAPP_GROUP_LINK}

{UI.ICONS['lock']} <b>Important:</b> Do not share these links!
{UI.ICONS['rocket']} Welcome to the Premium Family!
"""
            )
            
            logger.info(f"Admin finalized approval for user {target_id}")
            
        except Exception as e:
            logger.error(f"Error in final approve: {e}")
            await query.edit_message_text(f"{UI.ICONS['error']} Error: {e}")
        return
    
    # Admin: Reject payment
    if data.startswith('rejectpay_'):
        try:
            target_id = int(data.split('_')[1])
            context.user_data['reject_id'] = target_id
            context.user_data['reject_payment'] = True
            
            # Remove buttons from admin message
            await query.edit_message_reply_markup(reply_markup=None)
            
            original_text = query.message.caption or ""
            updated_text = f"{original_text}\n\n{UI.ICONS['error']} <b>ACTION TAKEN: REJECTING PAYMENT</b> ❌\n<i>Waiting for rejection reason...</i>"
            
            await query.edit_message_caption(caption=updated_text, parse_mode=ParseMode.HTML)
            
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"{UI.ICONS['error']} <b>Payment Rejection</b>\n\nUser ID: <code>{target_id}</code>\n\nPlease type the reason for payment rejection:"
            )
            
        except Exception as e:
            logger.error(f"Error in reject payment: {e}")
            await query.edit_message_text(f"{UI.ICONS['error']} Error: {e}")
        return

async def handle_text(update: Update, context):
    """Handle text messages with validation"""
    user_id = update.effective_user.id
    text = update.message.text
    
    user_data = get_user(user_id)
    if not user_data:
        await update.message.reply_text(
            f"{UI.ICONS['warning']} Please send /start to begin registration.",
            parse_mode=ParseMode.HTML
        )
        return
    
    step = user_data[7]
    
    # Handle full name
    if step == 'name_pending':
        if len(text) < 2:
            await update.message.reply_text(
                f"{UI.ICONS['error']} Name too short. Please enter your full name:",
                parse_mode=ParseMode.HTML
            )
            return
        
        update_user(user_id, 'full_name', text)
        update_user(user_id, 'current_step', 'email_pending')
        
        await update.message.reply_text(
            f"{UI.ICONS['success']} Name saved: <b>{text}</b>\n\n"
            f"{UI.ICONS['email']} Step 2 of 4: Please enter your email address:",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Handle email
    if step == 'email_pending':
        if "@" not in text or "." not in text.split('@')[-1]:
            await update.message.reply_text(
                f"{UI.ICONS['error']} Invalid email format!\n"
                f"Please enter a valid email (example: user@email.com):",
                parse_mode=ParseMode.HTML
            )
            return
        
        update_user(user_id, 'email', text)
        update_user(user_id, 'current_step', 'proof_pending')
        
        await update.message.reply_text(
            f"{UI.ICONS['success']} Email saved: <b>{text}</b>\n\n"
            f"{UI.ICONS['info']} Step 3 of 4: Please send screenshot of your purchase proof:",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Handle WhatsApp
    if step == 'whatsapp_pending':
        clean = re.sub(r'[\s\-\(\)\.]', '', text)
        if not re.match(r'^\+\d{10,15}$', clean):
            await update.message.reply_text(
                f"{UI.ICONS['error']} Invalid format!\n"
                f"Please use international format: <b>+923001234567</b>",
                parse_mode=ParseMode.HTML
            )
            return
        
        update_user(user_id, 'whatsapp', clean)
        update_user(user_id, 'current_step', 'info_submitted')
        
        await update.message.reply_text(
            f"{UI.ICONS['success']} <b>Application Submitted SuccessFully!</b>\n\n"
            f"{UI.ICONS['wait']} Your information has been sent for review.\n"
            f"You will be notified once approved.",
			⏳ *What happens next?*
            • Admin will review your application within 24 hours
            • You'll receive approval notification here
            • Then you can complete payment to join

            📊 *Your Application Status:* PENDING REVIEW

            🔔 *You'll be notified as soon as admin approves!*

            ⚠️ *Please do not send multiple applications.*
            """
            parse_mode=ParseMode.HTML
        )
        
        # Send to admin with action buttons
        keyboard = [
            [
                InlineKeyboardButton(f"{UI.ICONS['success']} Approve", callback_data=f'approve_{user_id}'),
                InlineKeyboardButton(f"{UI.ICONS['error']} Reject", callback_data=f'reject_{user_id}')
            ]
        ]
        
        admin_text = f"""
{UI.ICONS['star']} <b>NEW APPLICATION</b> {UI.ICONS['star']}

{UI.ICONS['user']} User: @{user_data[1] or 'N/A'}
{UI.ICONS['id']} ID: <code>{user_id}</code>
{UI.ICONS['user']} Name: <b>{user_data[2]}</b>
{UI.ICONS['email']} Email: <b>{user_data[3]}</b>
{UI.ICONS['phone']} WhatsApp: <code>{clean}</code>
{UI.ICONS['info']} Type: <b>{user_data[5]}</b>

{UI.ICONS['time']} Received: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        if user_data[6]:  # If proof photo exists
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
    
    # Handle rejection reason
    if 'reject_id' in context.user_data:
        target_id = context.user_data['reject_id']
        is_payment = context.user_data.get('reject_payment', False)
        
        reason_header = "Payment Rejected" if is_payment else "Application Rejected"
        
        await context.bot.send_message(
            chat_id=target_id,
            text=f"""
{UI.ICONS['error']} <b>{reason_header}</b>

Reason: <i>{text}</i>

If you believe this is an error, please contact support.
"""
        )
        
        await update.message.reply_text(
            f"{UI.ICONS['success']} Rejection sent to user {target_id}.",
            parse_mode=ParseMode.HTML
        )
        
        del context.user_data['reject_id']
        if 'reject_payment' in context.user_data:
            del context.user_data['reject_payment']
        return

async def handle_photo(update: Update, context):
    """Handle photo uploads with duplicate detection"""
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    if not user_data:
        return
    
    step = user_data[7]
    admin_approved = user_data[12]
    status = user_data[11]
    
    # First proof (purchase proof)
    if step == 'proof_pending':
        file_id = update.message.photo[-1].file_id
        update_user(user_id, 'proof_file_id', file_id)
        update_user(user_id, 'current_step', 'whatsapp_pending')
        
        await update.message.reply_text(
            f"{UI.ICONS['success']} Proof received!\n\n"
            f"{UI.ICONS['phone']} Step 4 of 4: Please enter your WhatsApp number\n"
            f"<i>Format: +923001234567</i>",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Payment proof
    if admin_approved == 1 and status == 'payment_pending':
        photo = update.message.photo[-1]
        
        # Check for duplicate screenshots
        try:
            file = await photo.get_file()
            bytes_data = await file.download_as_bytearray()
            hash_val = hashlib.md5(bytes_data).hexdigest()
        except Exception as e:
            logger.error(f"Error processing photo: {e}")
            await update.message.reply_text(
                f"{UI.ICONS['error']} Error processing image. Please try again.",
                parse_mode=ParseMode.HTML
            )
            return
        
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT 1 FROM screenshots WHERE file_hash = ?", (hash_val,))
        if c.fetchone():
            await update.message.reply_text(
                f"{UI.ICONS['error']} <b>Duplicate Screenshot Detected!</b>\n\n"
                f"This screenshot has already been used. Please send a unique payment proof.",
                parse_mode=ParseMode.HTML
            )
            conn.close()
            return
        
        # Save hash and update user
        c.execute("INSERT INTO screenshots (file_hash, user_id, used_at) VALUES (?, ?, ?)", 
                  (hash_val, user_id, datetime.now()))
        c.execute("""
            UPDATE users 
            SET payment_file_id = ?, payment_hash = ?, current_step = 'payment_submitted', status = 'payment_verification' 
            WHERE user_id = ?
        """, (photo.file_id, hash_val, user_id))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            f"{UI.ICONS['wait']} <b>Payment Received!</b>\n\n"
            f"Your payment is being verified by our team.\n"
            f"You will receive access links shortly.",
            parse_mode=ParseMode.HTML
        )
        
        # Send to admin for final verification
        keyboard = [
            [
                InlineKeyboardButton(f"{UI.ICONS['success']} Approve & Send Links", callback_data=f'final_{user_id}'),
                InlineKeyboardButton(f"{UI.ICONS['error']} Reject Payment", callback_data=f'rejectpay_{user_id}')
            ]
        ]
        
        admin_text = f"""
{UI.ICONS['money']} <b>PAYMENT VERIFICATION REQUIRED</b>

{UI.ICONS['user']} User: @{user_data[1] or 'N/A'}
{UI.ICONS['id']} ID: <code>{user_id}</code>
{UI.ICONS['user']} Name: <b>{user_data[2]}</b>
{UI.ICONS['money']} Method: <b>{user_data[8]}</b>
{UI.ICONS['time']} Submitted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{UI.ICONS['warning']} Please verify payment and approve/reject:
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
    """Initialize and run the bot"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Startup message
    print("╔════════════════════════════════════╗")
    print("║     🤖 BOT STARTED SUCCESSFULLY    ║")
    print("╠════════════════════════════════════╣")
    print(f"║ Admin ID: {ADMIN_ID}")
    print(f"║ Binance: {BINANCE_EMAIL}")
    print(f"║ Easypaisa: {EASYPAYSA_NUMBER}")
    print("╚════════════════════════════════════╝")
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
