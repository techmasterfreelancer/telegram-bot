import logging
import sqlite3
import hashlib
import re
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ============= YOUR DETAILS =============

BOT_TOKEN = "8535390425:AAE-K_QBPRw7e23GoWnGzCISz7T6pjpBLjQ"
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

logging.basicConfig(
    format='%(asctime)s │ %(name)s │ %(levelname)s │ %(message)s',
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

# ============= PREMIUM UI DESIGN =============

class PremiumUI:
    """Luxury UI Components"""
    
    ICONS = {
        'crown': '👑',
        'diamond': '💎',
        'star': '⭐',
        'sparkles': '✨',
        'fire': '🔥',
        'rocket': '🚀',
        'shield': '🛡️',
        'crown_gold': '🤴',
        'vip': '🎖️',
        'medal': '🏆',
        'money': '💵',
        'money_bag': '💰',
        'phone': '📱',
        'email': '📧',
        'id': '🆔',
        'globe': '🌐',
        'check': '✅',
        'cross': '❌',
        'warning': '⚠️',
        'info': 'ℹ️',
        'clock': '⏰',
        'hourglass': '⏳',
        'bell': '🔔',
        'lock': '🔒',
        'unlock': '🔓',
        'arrow': '➤',
        'bullet': '•',
        'heart': '❤️',
        'trophy': '🏆',
        'gem': '💎',
        'crown2': '👸'
    }
    
    DECORATORS = {
        'top': '╔════════════════════════════════════╗',
        'bottom': '╚════════════════════════════════════╝',
        'middle': '╠════════════════════════════════════╣',
        'line': '━',
        'star_line': '✦✦✦✦✦✦✦✦✦✦✦✦✦✦✦✦✦✦✦✦✦✦✦✦✦✦✦',
        'diamond_line': '💎💎💎💎💎💎💎💎💎💎💎💎💎💎💎'
    }
    
    @staticmethod
    def header(text, icon='👑'):
        return f"""
{PremiumUI.DECORATORS['top']}
{icon}  {text.center(30)}  {icon}
{PremiumUI.DECORATORS['bottom']}"""
    
    @staticmethod
    def section(title, content, icon='📋'):
        separator = '─' * 38
        return f"""
┌─ {icon} {title} {'─' * (33 - len(title))}┐
│
{content}
│
└{separator}┘"""
    
    @staticmethod
    def info_box(title, items, icon='ℹ️'):
        content = '\n'.join([f"  {PremiumUI.ICONS['bullet']} {item}" for item in items])
        return f"""
╔═══ {icon} {title} ═══╗
{content}
╚{'═' * 40}╝"""
    
    @staticmethod
    def step_indicator(current, total):
        filled = '●' * current
        empty = '○' * (total - current)
        return f"""
{PremiumUI.ICONS['diamond']} Progress: [{filled}{empty}] {current}/{total} {PremiumUI.ICONS['diamond']}"""
    
    @staticmethod
    def button(text, callback_data, style='premium'):
        styles = {
            'premium': '💎',
            'gold': '👑',
            'success': '✨',
            'danger': '🚫',
            'info': '📱',
            'money': '💰'
        }
        icon = styles.get(style, '💎')
        return InlineKeyboardButton(f"{icon} {text}", callback_data=callback_data)

# ============= PROFESSIONAL MESSAGE TEMPLATES =============

class ProfessionalMessages:
    """High-quality professional messages"""
    
    @staticmethod
    def welcome(first_name):
        return f"""
{PremiumUI.DECORATORS['diamond_line']}

{PremiumUI.ICONS['crown']} <b>WELCOME TO THE ELITE CIRCLE</b> {PremiumUI.ICONS['crown']}

Assalam-o-Alaikum, <b>{first_name}</b>! {PremiumUI.ICONS['sparkles']}

{PremiumUI.DECORATORS['star_line']}

<b>You are about to join an Exclusive Premium Community</b> {PremiumUI.ICONS['vip']}

{PremiumUI.info_box('WHAT YOU GET', [
    'VIP Access to Premium Groups ' + PremiumUI.ICONS['crown'],
    'Exclusive Content & Resources ' + PremiumUI.ICONS['gem'],
    'Direct Expert Support ' + PremiumUI.ICONS['shield'],
    'Weekly Live Classes (Sunday) ' + PremiumUI.ICONS['fire'],
    'Lifetime Membership Benefits ' + PremiumUI.ICONS['trophy']
], PremiumUI.ICONS['star'])}

{PremiumUI.section('IMPORTANT NOTICE', f'''
  {PremiumUI.ICONS['warning']} Please provide accurate information
  {PremiumUI.ICONS['warning']} Double-check before submitting
  {PremiumUI.ICONS['warning']} Rejected forms cannot be re-applied
  {PremiumUI.ICONS['info']} Your data is secure with us''', PremiumUI.ICONS['bell'])}

{PremiumUI.DECORATORS['middle']}

<b>Ready to begin your journey?</b> {PremiumUI.ICONS['rocket']}

<i>Select your membership type below:</i>
"""
    
    @staticmethod
    def step_name():
        return f"""
{PremiumUI.step_indicator(1, 4)}

{PremiumUI.header('PERSONAL INFORMATION', PremiumUI.ICONS['id'])}

{PremiumUI.ICONS['crown']} <b>Step 1: Full Name Verification</b>

Please enter your <b>complete full name</b> as it appears on your official ID card.

{PremiumUI.info_box('GUIDELINES', [
    'Use your real full name',
    'Match with your ID card exactly',
    'Avoid nicknames or short forms'
], PremiumUI.ICONS['info'])}

{PremiumUI.ICONS['arrow']} <b>Type your full name below:</b>
"""
    
    @staticmethod
    def step_email(name):
        return f"""
{PremiumUI.step_indicator(2, 4)}

{PremiumUI.header('CONTACT DETAILS', PremiumUI.ICONS['email'])}

{PremiumUI.ICONS['check']} <b>Name Confirmed:</b> <code>{name}</code>

{PremiumUI.ICONS['crown']} <b>Step 2: Email Address</b>

Please provide your <b>active email address</b> for important updates.

{PremiumUI.info_box('REQUIREMENTS', [
    'Must be a valid email format',
    'Should be actively used by you',
    'Will be used for notifications'
], PremiumUI.ICONS['email'])}

{PremiumUI.ICONS['arrow']} <b>Enter your email address:</b>
"""
    
    @staticmethod
    def step_proof():
        return f"""
{PremiumUI.step_indicator(3, 4)}

{PremiumUI.header('VERIFICATION DOCUMENT', PremiumUI.ICONS['shield'])}

{PremiumUI.ICONS['crown']} <b>Step 3: Upload Purchase Proof</b>

Please upload a <b>clear screenshot</b> of your purchase receipt or payment proof.

{PremiumUI.info_box('UPLOAD REQUIREMENTS', [
    'Screenshot must be clear & readable',
    'Date and time should be visible',
    'Transaction details must show',
    'No edited or fake screenshots',
    'File size: Max 5MB'
], PremiumUI.ICONS['warning'])}

{PremiumUI.ICONS['arrow']} <b>Send your screenshot now:</b>
"""
    
    @staticmethod
    def step_whatsapp():
        return f"""
{PremiumUI.step_indicator(4, 4)}

{PremiumUI.header('FINAL STEP', PremiumUI.ICONS['phone'])}

{PremiumUI.ICONS['crown']} <b>Step 4: WhatsApp Verification</b>

Please provide your <b>WhatsApp number</b> with country code.

{PremiumUI.info_box('FORMAT GUIDE', [
    'Use international format',
    'Include country code',
    'Example: +92 300 1234567',
    'No spaces or dashes needed'
], PremiumUI.ICONS['phone'])}

{PremiumUI.ICONS['arrow']} <b>Enter your WhatsApp number:</b>
"""
    
    @staticmethod
    def application_submitted():
        return f"""
{PremiumUI.DECORATORS['diamond_line']}

{PremiumUI.ICONS['check']} <b>APPLICATION SUBMITTED SUCCESSFULLY</b> {PremiumUI.ICONS['check']}

{PremiumUI.section('SUBMISSION DETAILS', f'''
  {PremiumUI.ICONS['info']} Status: Under Review
  {PremiumUI.ICONS['clock']} Estimated Time: 5-15 minutes
  {PremiumUI.ICONS['bell']} You will receive a notification''', PremiumUI.ICONS['hourglass'])}

{PremiumUI.ICONS['warning']} <i>Please do not send multiple messages</i>

{PremiumUI.DECORATORS['star_line']}
"""
    
    @staticmethod
    def approved_payment():
        return f"""
{PremiumUI.DECORATORS['diamond_line']}

{PremiumUI.ICONS['trophy']} <b>CONGRATULATIONS! APPROVED</b> {PremiumUI.ICONS['trophy']}

{PremiumUI.section('APPLICATION STATUS', f'''
  {PremiumUI.ICONS['check']} Your application has been APPROVED
  {PremiumUI.ICONS['money']} Payment Required: {MEMBERSHIP_FEE}
  {PremiumUI.ICONS['clock']} Complete payment to get instant access''', PremiumUI.ICONS['medal'])}

{PremiumUI.DECORATORS['middle']}

<b>Select your preferred payment method:</b>
"""
    
    @staticmethod
    def payment_binance():
        return f"""
{PremiumUI.header('BINANCE PAYMENT', PremiumUI.ICONS['money'])}

{PremiumUI.ICONS['crown']} <b>Secure Payment Gateway</b>

{PremiumUI.section('TRANSFER DETAILS', f'''
  {PremiumUI.ICONS['money']} Amount: <b>{MEMBERSHIP_FEE}</b>
  {PremiumUI.ICONS['globe']} Network: <code>TRC20</code>
  
  {PremiumUI.ICONS['email']} Email: <code>{BINANCE_EMAIL}</code>
  {PremiumUI.ICONS['id']} ID: <code>{BINANCE_ID}</code>''', PremiumUI.ICONS['shield'])}

{PremiumUI.info_box('IMPORTANT', [
    'Send EXACT amount only',
    'Use TRC20 network only',
    'Save transaction screenshot',
    'Upload screenshot after payment'
], PremiumUI.ICONS['warning'])}

{PremiumUI.ICONS['arrow']} <b>After payment, send screenshot here</b>
"""
    
    @staticmethod
    def payment_easypaisa():
        return f"""
{PremiumUI.header('EASYPAYSA PAYMENT', PremiumUI.ICONS['phone'])}

{PremiumUI.ICONS['crown']} <b>Secure Payment Gateway</b>

{PremiumUI.section('TRANSFER DETAILS', f'''
  {PremiumUI.ICONS['money']} Amount: <b>{MEMBERSHIP_FEE}</b>
  
  {PremiumUI.ICONS['id']} Account Name: <b>{EASYPAYSA_NAME}</b>
  {PremiumUI.ICONS['phone']} Number: <code>{EASYPAYSA_NUMBER}</code>''', PremiumUI.ICONS['shield'])}

{PremiumUI.info_box('IMPORTANT', [
    'Send EXACT amount only',
    'Use registered Easypaisa',
    'Save transaction screenshot',
    'Upload screenshot after payment'
], PremiumUI.ICONS['warning'])}

{PremiumUI.ICONS['arrow']} <b>After payment, send screenshot here</b>
"""
    
    @staticmethod
    def payment_verifying():
        return f"""
{PremiumUI.DECORATORS['star_line']}

{PremiumUI.ICONS['hourglass']} <b>PAYMENT VERIFICATION IN PROGRESS</b> {PremiumUI.ICONS['hourglass']}

{PremiumUI.section('STATUS UPDATE', f'''
  {PremiumUI.ICONS['check']} Payment screenshot received
  {PremiumUI.ICONS['clock']} Under admin verification
  {PremiumUI.ICONS['info']} Estimated time: 5-10 minutes''', PremiumUI.ICONS['shield'])}

{PremiumUI.ICONS['warning']} <i>Please wait patiently. Do not send multiple messages.</i>

{PremiumUI.DECORATORS['diamond_line']}
"""
    
    @staticmethod
    def access_granted():
        return f"""
{PremiumUI.DECORATORS['diamond_line']}
{PremiumUI.DECORATORS['diamond_line']}

{PremiumUI.ICONS['trophy']} <b>WELCOME TO THE ELITE FAMILY!</b> {PremiumUI.ICONS['trophy']}

{PremiumUI.ICONS['fire']} <b>YOUR ACCESS IS NOW ACTIVE</b> {PremiumUI.ICONS['fire']}

{PremiumUI.section('YOUR EXCLUSIVE LINKS', f'''
  {PremiumUI.ICONS['crown']} <b>Telegram VIP Group:</b>
  {TELEGRAM_GROUP_LINK}
  
  {PremiumUI.ICONS['phone']} <b>WhatsApp Elite Circle:</b>
  {WHATSAPP_GROUP_LINK}''', PremiumUI.ICONS['unlock'])}

{PremiumUI.info_box('SUNDAY LIVE CLASS', [
    'Every Sunday Night',
    'Live Q&A Session',
    'Issue Resolution',
    'Premium Tips & Tricks'
], PremiumUI.ICONS['fire'])}

{PremiumUI.section('SECURITY NOTICE', f'''
  {PremiumUI.ICONS['warning']} These links are for YOU only
  {PremiumUI.ICONS['cross']} Sharing = Permanent Ban
  {PremiumUI.ICONS['shield']} Your account is monitored''', PremiumUI.ICONS['lock'])}

{PremiumUI.ICONS['rocket']} <b>Your premium journey starts NOW!</b>

{PremiumUI.DECORATORS['diamond_line']}
{PremiumUI.DECORATORS['diamond_line']}
"""
    
    @staticmethod
    def admin_new_application(user_data, whatsapp):
        return f"""
{PremiumUI.ICONS['bell']} <b>NEW APPLICATION RECEIVED</b> {PremiumUI.ICONS['bell']}

{PremiumUI.DECORATORS['line'] * 20}

<b>Applicant Details:</b>
{PremiumUI.ICONS['id']} <b>User ID:</b> <code>{user_data[0]}</code>
{PremiumUI.ICONS['id']} <b>Username:</b> @{user_data[1] or 'N/A'}
{PremiumUI.ICONS['crown']} <b>Full Name:</b> {user_data[2]}
{PremiumUI.ICONS['email']} <b>Email:</b> {user_data[3]}
{PremiumUI.ICONS['phone']} <b>WhatsApp:</b> <code>{whatsapp}</code>
{PremiumUI.ICONS['info']} <b>Type:</b> {user_data[5]}

{PremiumUI.DECORATORS['line'] * 20}

<i>Review and take action:</i>
"""
    
    @staticmethod
    def admin_payment_verify(user_data):
        return f"""
{PremiumUI.ICONS['money_bag']} <b>PAYMENT VERIFICATION REQUIRED</b> {PremiumUI.ICONS['money_bag']}

{PremiumUI.DECORATORS['line'] * 20}

<b>Member Details:</b>
{PremiumUI.ICONS['id']} <b>User ID:</b> <code>{user_data[0]}</code>
{PremiumUI.ICONS['id']} <b>Username:</b> @{user_data[1] or 'N/A'}
{PremiumUI.ICONS['crown']} <b>Name:</b> {user_data[2]}
{PremiumUI.ICONS['money']} <b>Method:</b> {user_data[8]}

{PremiumUI.DECORATORS['line'] * 20}

<i>Verify payment screenshot:</i>
"""
    
    @staticmethod
    def action_completed(action):
        timestamp = datetime.now().strftime('%H:%M:%S')
        icons = {
            'approved': PremiumUI.ICONS['check'],
            'rejected': PremiumUI.ICONS['cross'],
            'payment_verified': PremiumUI.ICONS['trophy'],
            'payment_rejected': PremiumUI.ICONS['cross']
        }
        icon = icons.get(action, PremiumUI.ICONS['check'])
        
        messages = {
            'approved': f"{icon} <b>APPROVED</b> at {timestamp}\nUser notified to complete payment",
            'rejected': f"{icon} <b>REJECTED</b> at {timestamp}\nUser has been notified",
            'payment_verified': f"{icon} <b>PAYMENT VERIFIED</b> at {timestamp}\nAccess links sent to user",
            'payment_rejected': f"{icon} <b>PAYMENT REJECTED</b> at {timestamp}\nAwaiting rejection reason"
        }
        
        return f"\n\n{PremiumUI.DECORATORS['line'] * 15}\n{messages.get(action, 'Action completed')}"

# ============= BOT FUNCTIONS =============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name
    
    user_data = get_user(user_id)
    
    if not user_data:
        create_user(user_id, user.username or "No username")
        
        keyboard = [
            [PremiumUI.button("Premium Subscription", "premium", "gold")],
            [PremiumUI.button("Product Purchase", "product", "premium")]
        ]
        
        await update.message.reply_text(
            ProfessionalMessages.welcome(first_name),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    status = user_data[11]
    admin_approved = user_data[12]
    step = user_data[7]
    
    if status == 'completed':
        await update.message.reply_text(
            ProfessionalMessages.access_granted(),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        return
    
    if admin_approved == 1 and status == 'payment_pending':
        keyboard = [
            [PremiumUI.button("Binance Pay", "binance", "money")],
            [PremiumUI.button("Easypaisa", "easypaisa", "info")]
        ]
        
        await update.message.reply_text(
            ProfessionalMessages.approved_payment(),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if step == 'info_submitted':
        await update.message.reply_text(
            f"""
{PremiumUI.ICONS['hourglass']} <b>APPLICATION UNDER REVIEW</b> {PremiumUI.ICONS['hourglass']}

{PremiumUI.DECORATORS['line'] * 20}

Your application is being reviewed by our admin team.
You will receive a notification once approved.

{PremiumUI.ICONS['clock']} <i>Estimated time: 5-15 minutes</i>

{PremiumUI.DECORATORS['line'] * 20}
""",
            parse_mode=ParseMode.HTML
        )
        return
    
    if step == 'payment_submitted':
        await update.message.reply_text(
            ProfessionalMessages.payment_verifying(),
            parse_mode=ParseMode.HTML
        )
        return
    
    # Resume steps with professional messages
    if step == 'name_pending':
        await update.message.reply_text(
            ProfessionalMessages.step_name(),
            parse_mode=ParseMode.HTML
        )
    elif step == 'email_pending':
        await update.message.reply_text(
            ProfessionalMessages.step_email(user_data[2]),
            parse_mode=ParseMode.HTML
        )
    elif step == 'proof_pending':
        await update.message.reply_text(
            ProfessionalMessages.step_proof(),
            parse_mode=ParseMode.HTML
        )
    elif step == 'whatsapp_pending':
        await update.message.reply_text(
            ProfessionalMessages.step_whatsapp(),
            parse_mode=ParseMode.HTML
        )
    else:
        keyboard = [
            [PremiumUI.button("Premium Subscription", "premium", "gold")],
            [PremiumUI.button("Product Purchase", "product", "premium")]
        ]
        await update.message.reply_text(
            ProfessionalMessages.welcome(first_name),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    if data in ['premium', 'product']:
        request_type = "Premium Subscription" if data == 'premium' else "Product Purchase"
        update_user(user_id, 'request_type', request_type)
        update_user(user_id, 'current_step', 'name_pending')
        
        await query.edit_message_text(
            ProfessionalMessages.step_name(),
            parse_mode=ParseMode.HTML
        )
        return
    
    if data in ['binance', 'easypaisa']:
        update_user(user_id, 'payment_method', data.capitalize())
        
        if data == 'binance':
            await query.edit_message_text(
                ProfessionalMessages.payment_binance(),
                parse_mode=ParseMode.HTML
            )
        else:
            await query.edit_message_text(
                ProfessionalMessages.payment_easypaisa(),
                parse_mode=ParseMode.HTML
            )
        return
    
    # Admin approve
    if data.startswith('approve_'):
        try:
            target_id = int(data.split('_')[1])
            
            conn = get_db()
            c = conn.cursor()
            c.execute("UPDATE users SET admin_approved = 1, status = 'payment_pending', current_step = 'payment_pending' WHERE user_id = ?", (target_id,))
            conn.commit()
            conn.close()
            
            # Remove buttons and update message
            await query.edit_message_reply_markup(reply_markup=None)
            
            original = query.message.text or query.message.caption or ""
            updated = original + ProfessionalMessages.action_completed('approved')
            
            if query.message.photo:
                await query.edit_message_caption(caption=updated, parse_mode=ParseMode.HTML)
            else:
                await query.edit_message_text(updated, parse_mode=ParseMode.HTML)
            
            # Notify user
            keyboard = [
                [PremiumUI.button("Binance Pay", "binance", "money")],
                [PremiumUI.button("Easypaisa", "easypaisa", "info")]
            ]
            
            await context.bot.send_message(
                chat_id=target_id,
                text=ProfessionalMessages.approved_payment(),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await query.edit_message_text(f"❌ Error: {e}")
        return
    
    # Admin reject
    if data.startswith('reject_'):
        try:
            target_id = int(data.split('_')[1])
            context.user_data['reject_id'] = target_id
            
            await query.edit_message_reply_markup(reply_markup=None)
            
            original = query.message.text or query.message.caption or ""
            updated = original + ProfessionalMessages.action_completed('rejected')
            
            if query.message.photo:
                await query.edit_message_caption(caption=updated, parse_mode=ParseMode.HTML)
            else:
                await query.edit_message_text(updated, parse_mode=ParseMode.HTML)
            
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"{PremiumUI.ICONS['cross']} <b>REJECTION REASON REQUIRED</b>\n\nUser ID: <code>{target_id}</code>\n\nPlease type the reason:"
            )
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await query.edit_message_text(f"❌ Error: {e}")
        return
    
    # Final approve
    if data.startswith('final_'):
        try:
            target_id = int(data.split('_')[1])
            
            conn = get_db()
            c = conn.cursor()
            c.execute("UPDATE users SET status = 'completed' WHERE user_id = ?", (target_id,))
            conn.commit()
            conn.close()
            
            await query.edit_message_reply_markup(reply_markup=None)
            
            original = query.message.caption or ""
            updated = original + ProfessionalMessages.action_completed('payment_verified')
            
            await query.edit_message_caption(caption=updated, parse_mode=ParseMode.HTML)
            
            await context.bot.send_message(
                chat_id=target_id,
                text=ProfessionalMessages.access_granted(),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await query.edit_message_text(f"❌ Error: {e}")
        return
    
    # Reject payment
    if data.startswith('rejectpay_'):
        try:
            target_id = int(data.split('_')[1])
            context.user_data['reject_id'] = target_id
            context.user_data['reject_payment'] = True
            
            await query.edit_message_reply_markup(reply_markup=None)
            
            original = query.message.caption or ""
            updated = original + ProfessionalMessages.action_completed('payment_rejected')
            
            await query.edit_message_caption(caption=updated, parse_mode=ParseMode.HTML)
            
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"{PremiumUI.ICONS['cross']} <b>PAYMENT REJECTION REASON</b>\n\nUser ID: <code>{target_id}</code>\n\nPlease type the reason:"
            )
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await query.edit_message_text(f"❌ Error: {e}")
        return

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    user_data = get_user(user_id)
    if not user_data:
        await update.message.reply_text("Please send /start to begin")
        return
    
    step = user_data[7]
    
    # Name
    if step == 'name_pending':
        if len(text) < 2:
            await update.message.reply_text(
                f"{PremiumUI.ICONS['cross']} <b>Name too short!</b>\n\nPlease enter your full name:",
                parse_mode=ParseMode.HTML
            )
            return
        
        update_user(user_id, 'full_name', text)
        update_user(user_id, 'current_step', 'email_pending')
        
        await update.message.reply_text(
            ProfessionalMessages.step_email(text),
            parse_mode=ParseMode.HTML
        )
        return
    
    # Email
    if step == 'email_pending':
        if "@" not in text or "." not in text.split('@')[-1]:
            await update.message.reply_text(
                f"{PremiumUI.ICONS['cross']} <b>Invalid email format!</b>\n\nPlease enter a valid email:",
                parse_mode=ParseMode.HTML
            )
            return
        
        update_user(user_id, 'email', text)
        update_user(user_id, 'current_step', 'proof_pending')
        
        await update.message.reply_text(
            ProfessionalMessages.step_proof(),
            parse_mode=ParseMode.HTML
        )
        return
    
    # WhatsApp
    if step == 'whatsapp_pending':
        clean = re.sub(r'[\s\-\(\)\.]', '', text)
        if not re.match(r'^\+\d{10,15}$', clean):
            await update.message.reply_text(
                f"{PremiumUI.ICONS['cross']} <b>Invalid format!</b>\n\nPlease use international format:\n<code>+923001234567</code>",
                parse_mode=ParseMode.HTML
            )
            return
        
        update_user(user_id, 'whatsapp', clean)
        update_user(user_id, 'current_step', 'info_submitted')
        
        await update.message.reply_text(
            ProfessionalMessages.application_submitted(),
            parse_mode=ParseMode.HTML
        )
        
        # Send to admin
        keyboard = [
            [
                PremiumUI.button("Approve Application", f"approve_{user_id}", "success"),
                PremiumUI.button("Reject", f"reject_{user_id}", "danger")
            ]
        ]
        
        admin_msg = ProfessionalMessages.admin_new_application(user_data, clean)
        
        if user_data[6]:
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=user_data[6],
                caption=admin_msg,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_msg,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return
    
    # Rejection reason
    if 'reject_id' in context.user_data:
        target_id = context.user_data['reject_id']
        is_payment = context.user_data.get('reject_payment', False)
        
        header = "Payment Rejected" if is_payment else "Application Rejected"
        
        await context.bot.send_message(
            chat_id=target_id,
            text=f"""
{PremiumUI.ICONS['cross']} <b>{header}</b> {PremiumUI.ICONS['cross']}

<b>Reason:</b> <i>{text}</i>

{PremiumUI.DECORATORS['line'] * 20}

If you believe this is an error, please contact support.
"""
        )
        
        await update.message.reply_text(
            f"{PremiumUI.ICONS['check']} <b>Rejection sent to user {target_id}</b>",
            parse_mode=ParseMode.HTML
        )
        
        del context.user_data['reject_id']
        if 'reject_payment' in context.user_data:
            del context.user_data['reject_payment']
        return

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        await update.message.reply_text(
            ProfessionalMessages.step_whatsapp(),
            parse_mode=ParseMode.HTML
        )
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
            await update.message.reply_text(
                f"""
{PremiumUI.ICONS['cross']} <b>DUPLICATE SCREENSHOT DETECTED!</b> {PremiumUI.ICONS['cross']}

{PremiumUI.DECORATORS['line'] * 20}

This screenshot has already been used.
Please send a new, original payment proof.

{PremiumUI.ICONS['warning']} <i>Duplicate uploads may result in ban</i>
"""
            )
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
        
        await update.message.reply_text(
            ProfessionalMessages.payment_verifying(),
            parse_mode=ParseMode.HTML
        )
        
        # Send to admin
        keyboard = [
            [
                PremiumUI.button("Verify & Grant Access", f"final_{user_id}", "gold"),
                PremiumUI.button("Reject Payment", f"rejectpay_{user_id}", "danger")
            ]
        ]
        
        admin_msg = ProfessionalMessages.admin_payment_verify(user_data)
        
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo.file_id,
            caption=admin_msg,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

def main():
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("""
    ╔══════════════════════════════════════╗
    ║     👑 PREMIUM BOT ACTIVATED 👑      ║
    ║     Professional & Beautiful         ║
    ╚══════════════════════════════════════╝
    """)
    
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    main()
