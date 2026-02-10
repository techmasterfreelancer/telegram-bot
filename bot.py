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

# Premium Logging Setup
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

# ============= LUXURY UI COMPONENTS =============

class LuxuryUI:
    """Premium UI Components for VIP Experience"""
    
    # Premium emojis collection
    EMOJIS = {
        'crown': '👑',
        'diamond': '💎',
        'star': '⭐',
        'sparkles': '✨',
        'fire': '🔥',
        'rocket': '🚀',
        'crown_gold': '🤴',
        'shield': '🛡️',
        'key': '🔐',
        'door': '🚪',
        'vip': '🎖️',
        'medal': '🏆',
        'money_bag': '💰',
        'credit_card': '💳',
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
        'arrow_right': '➤',
        'arrow_forward': '→',
        'bullet': '•',
        'divider': '━━━━━━━━━━━━━━━',
        'double_divider': '╔═══════════════════╗\n╚═══════════════════╝',
        'corner_tl': '╔',
        'corner_tr': '╗',
        'corner_bl': '╚',
        'corner_br': '╝',
        'line_h': '═',
        'line_v': '║',
        'bullet_star': '✦',
        'bullet_diamond': '◆',
        'bullet_arrow': '▸'
    }
    
    @staticmethod
    def luxury_box(title, content, width=40):
        """Create a luxury bordered box"""
        top = f"╔{'═' * (width-2)}╗"
        title_line = f"║{title.center(width-2)}║"
        separator = f"╠{'═' * (width-2)}╣"
        bottom = f"╚{'═' * (width-2)}╝"
        
        lines = content.split('\n')
        content_lines = []
        for line in lines:
            if len(line) > width-4:
                # Truncate long lines
                line = line[:width-7] + "..."
            content_lines.append(f"║ {line.ljust(width-4)} ║")
        
        return f"{top}\n{title_line}\n{separator}\n" + '\n'.join(content_lines) + f"\n{bottom}"
    
    @staticmethod
    def status_banner(status):
        """Premium status banners"""
        banners = {
            'new': f"{LuxuryUI.EMOJIS['star']} NEW MEMBER",
            'pending': f"{LuxuryUI.EMOJIS['hourglass']} UNDER REVIEW",
            'approved': f"{LuxuryUI.EMOJIS['crown']} APPROVED",
            'rejected': f"{LuxuryUI.EMOJIS['cross']} DECLINED",
            'completed': f"{LuxuryUI.EMOJIS['medal']} VERIFIED MEMBER",
            'payment_pending': f"{LuxuryUI.EMOJIS['money_bag']} PAYMENT REQUIRED",
            'payment_verification': f"{LuxuryUI.EMOJIS['clock']} VERIFYING PAYMENT"
        }
        return banners.get(status, status.upper())
    
    @staticmethod
    def gradient_text(text, style='gold'):
        """Simulate gradient with Unicode"""
        if style == 'gold':
            return f"✨ {text} ✨"
        elif style == 'vip':
            return f"👑 {text} 👑"
        elif style == 'alert':
            return f"🔔 {text} 🔔"
        return text
    
    @staticmethod
    def button(text, callback_data, style='premium'):
        """Premium styled buttons"""
        styles = {
            'premium': ('💎', 'primary'),
            'gold': ('👑', 'success'),
            'silver': ('🥈', 'secondary'),
            'danger': ('🚫', 'danger'),
            'success': ('✨', 'success'),
            'warning': ('⚡', 'warning')
        }
        emoji, _ = styles.get(style, ('💎', 'primary'))
        return InlineKeyboardButton(f"{emoji} {text}", callback_data=callback_data)

# ============= PREMIUM MESSAGE TEMPLATES =============

class MessageTemplates:
    """High-quality message templates"""
    
    @staticmethod
    def welcome(first_name):
        return f"""
{LuxuryUI.EMOJIS['crown']} <b>WELCOME TO THE ELITE</b> {LuxuryUI.EMOJIS['crown']}

Greetings, <b>{first_name}</b>! 

{LuxuryUI.EMOJIS['sparkles']} You are about to enter an <b>Exclusive Premium Community</b> {LuxuryUI.EMOJIS['sparkles']}

{LuxuryUI.EMOJIS['divider']}

<b>What awaits you inside:</b>
{LuxuryUI.EMOJIS['bullet_diamond']} VIP Access to Premium Groups
{LuxuryUI.EMOJIS['bullet_diamond']} Exclusive Content & Resources  
{LuxuryUI.EMOJIS['bullet_diamond']} Direct Support & Networking
{LuxuryUI.EMOJIS['bullet_diamond']} Lifetime Membership Benefits

{LuxuryUI.EMOJIS['divider']}

<i>Please select your membership type below to begin verification:</i>
"""
    
    @staticmethod
    def step_header(step_num, total_steps, title):
        return f"""
{LuxuryUI.EMOJIS['diamond']} <b>VERIFICATION STEP {step_num}/{total_steps}</b> {LuxuryUI.EMOJIS['diamond']}

<b>{title}</b>

{LuxuryUI.EMOJIS['divider']}
"""
    
    @staticmethod
    def payment_info(method):
        if method == 'binance':
            return f"""
{LuxuryUI.EMOJIS['money_bag']} <b>SECURE PAYMENT GATEWAY</b> {LuxuryUI.EMOJIS['money_bag']}

{LuxuryUI.luxury_box('BINANCE PAYMENT DETAILS', f'''
Amount: {MEMBERSHIP_FEE}
Network: TRC20 (Tron)

Email: {BINANCE_EMAIL}
ID: {BINANCE_ID}

Status: Awaiting Transfer...
''', 42)}

{LuxuryUI.EMOJIS['warning']} <i>Please send exact amount to avoid delays</i>
{LuxuryUI.EMOJIS['info']} Screenshot required after payment
"""
        else:
            return f"""
{LuxuryUI.EMOJIS['phone']} <b>SECURE PAYMENT GATEWAY</b> {LuxuryUI.EMOJIS['phone']}

{LuxuryUI.luxury_box('EASYPAYSA DETAILS', f'''
Amount: {MEMBERSHIP_FEE}

Account: {EASYPAYSA_NAME}
Number: {EASYPAYSA_NUMBER}

Status: Awaiting Transfer...
''', 42)}

{LuxuryUI.EMOJIS['warning']} <i>Please send exact amount to avoid delays</i>
{LuxuryUI.EMOJIS['info']} Screenshot required after payment
"""
    
    @staticmethod
    def admin_notification(user_data, whatsapp, is_payment=False):
        if is_payment:
            return f"""
{LuxuryUI.EMOJIS['money_bag']} <b>PAYMENT VERIFICATION QUEUE</b> {LuxuryUI.EMOJIS['money_bag']}

{LuxuryUI.EMOJIS['divider']}

<b>Member Details:</b>
{LuxuryUI.EMOJIS['bullet']} User: @{user_data[1] or 'N/A'}
{LuxuryUI.EMOJIS['bullet']} ID: <code>{user_data[0]}</code>
{LuxuryUI.EMOJIS['bullet']} Name: {user_data[2]}
{LuxuryUI.EMOJIS['bullet']} Method: {user_data[8]}

{LuxuryUI.EMOJIS['divider']}

<i>Please verify payment screenshot and take action:</i>
"""
        else:
            return f"""
{LuxuryUI.EMOJIS['star']} <b>NEW MEMBER APPLICATION</b> {LuxuryUI.EMOJIS['star']}

{LuxuryUI.EMOJIS['divider']}

<b>Applicant Information:</b>
{LuxuryUI.EMOJIS['bullet']} Username: @{user_data[1] or 'N/A'}
{LuxuryUI.EMOJIS['bullet']} User ID: <code>{user_data[0]}</code>
{LuxuryUI.EMOJIS['bullet']} Full Name: {user_data[2]}
{LuxuryUI.EMOJIS['bullet']} Email: {user_data[3]}
{LuxuryUI.EMOJIS['bullet']} WhatsApp: <code>{whatsapp}</code>
{LuxuryUI.EMOJIS['bullet']} Type: {user_data[5]}

{LuxuryUI.EMOJIS['divider']}

<i>Review application and approve for payment:</i>
"""
    
    @staticmethod
    def success_access():
        return f"""
{LuxuryUI.EMOJIS['medal']} <b>WELCOME TO THE ELITE CIRCLE</b> {LuxuryUI.EMOJIS['medal']}

{LuxuryUI.EMOJIS['fire']} <b>VERIFICATION COMPLETE!</b> {LuxuryUI.EMOJIS['fire']}

{LuxuryUI.EMOJIS['divider']}

<b>Your Exclusive Access:</b>

{LuxuryUI.EMOJIS['diamond']} <b>Telegram VIP Group:</b>
{TELEGRAM_GROUP_LINK}

{LuxuryUI.EMOJIS['phone']} <b>WhatsApp Elite Circle:</b>
{WHATSAPP_GROUP_LINK}

{LuxuryUI.EMOJIS['divider']}

{LuxuryUI.EMOJIS['shield']} <b>Security Notice:</b>
These links are exclusive to you. Sharing will result in immediate ban.

{LuxuryUI.EMOJIS['rocket']} <b>Your journey begins now!</b>
"""
    
    @staticmethod
    def action_taken(action, timestamp=None):
        time_str = timestamp or datetime.now().strftime('%H:%M:%S')
        if action == 'approved':
            return f"\n\n{LuxuryUI.EMOJIS['check']} <b>ACTION COMPLETED</b> {LuxuryUI.EMOJIS['check']}\n<i>Approved at {time_str} • User notified</i>"
        elif action == 'rejected':
            return f"\n\n{LuxuryUI.EMOJIS['cross']} <b>ACTION COMPLETED</b> {LuxuryUI.EMOJIS['cross']}\n<i>Rejected at {time_str} • User notified</i>"
        elif action == 'payment_approved':
            return f"\n\n{LuxuryUI.EMOJIS['medal']} <b>PAYMENT VERIFIED</b> {LuxuryUI.EMOJIS['medal']}\n<i>Verified at {time_str} • Access granted</i>"
        elif action == 'payment_rejected':
            return f"\n\n{LuxuryUI.EMOJIS['cross']} <b>PAYMENT REJECTED</b> {LuxuryUI.EMOJIS['cross']}\n<i>Rejected at {time_str} • Awaiting reason</i>"

# ============= BOT FUNCTIONS =============

async def start(update: Update, context):
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name
    
    user_data = get_user(user_id)
    
    if not user_data:
        create_user(user_id, user.username or "No username")
        
        keyboard = [
            [LuxuryUI.button("Premium Subscription", "premium", "gold")],
            [LuxuryUI.button("Product Purchase", "product", "silver")]
        ]
        
        await update.message.reply_text(
            MessageTemplates.welcome(first_name),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    status = user_data[11]
    admin_approved = user_data[12]
    step = user_data[7]
    
    # Already completed
    if status == 'completed':
        await update.message.reply_text(
            MessageTemplates.success_access(),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        return
    
    # Approved, waiting for payment
    if admin_approved == 1 and status == 'payment_pending':
        text = f"""
{LuxuryUI.EMOJIS['crown']} <b>CONGRATULATIONS!</b> {LuxuryUI.EMOJIS['crown']}

{LuxuryUI.EMOJIS['check']} Your application has been <b>APPROVED</b>!

{LuxuryUI.EMOJIS['divider']}

<b>Next Step:</b> Complete your payment of {MEMBERSHIP_FEE}

{LuxuryUI.EMOJIS['info']} Select your preferred payment method:
"""
        keyboard = [
            [LuxuryUI.button("Binance Pay", "binance", "gold")],
            [LuxuryUI.button("Easypaisa", "easypaisa", "silver")]
        ]
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Pending review
    if step == 'info_submitted':
        await update.message.reply_text(
            f"""
{LuxuryUI.EMOJIS['hourglass']} <b>APPLICATION UNDER REVIEW</b> {LuxuryUI.EMOJIS['hourglass']}

{LuxuryUI.EMOJIS['divider']}

Your application is being reviewed by our admin team.
You will receive a notification once approved.

{LuxuryUI.EMOJIS['clock']} <i>Estimated time: 5-15 minutes</i>
""",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Payment verification pending
    if step == 'payment_submitted':
        await update.message.reply_text(
            f"""
{LuxuryUI.EMOJIS['clock']} <b>PAYMENT VERIFICATION</b> {LuxuryUI.EMOJIS['clock']}

{LuxuryUI.EMOJIS['divider']}

Your payment is being verified.
You will receive access links once confirmed.

{LuxuryUI.EMOJIS['info']} <i>Please do not send multiple screenshots</i>
""",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Resume incomplete steps
    if step == 'name_pending':
        await update.message.reply_text(
            MessageTemplates.step_header(1, 4, "Personal Information") + 
            "\nPlease enter your <b>full name</b> (as on official documents):",
            parse_mode=ParseMode.HTML
        )
    elif step == 'email_pending':
        await update.message.reply_text(
            MessageTemplates.step_header(2, 4, "Contact Details") +
            f"\n{Name: <b>{user_data[2]}</b>\n\nPlease enter your <b>email address</b>:",
            parse_mode=ParseMode.HTML
        )
    elif step == 'proof_pending':
        await update.message.reply_text(
            MessageTemplates.step_header(3, 4, "Purchase Verification") +
            "\nPlease upload screenshot of your <b>purchase receipt</b> or <b>proof</b>:",
            parse_mode=ParseMode.HTML
        )
    elif step == 'whatsapp_pending':
        await update.message.reply_text(
            MessageTemplates.step_header(4, 4, "Final Step") +
            "\nPlease enter your <b>WhatsApp number</b> with country code:\n" +
            "<i>Example: +92 300 1234567</i>",
            parse_mode=ParseMode.HTML
        )
    else:
        keyboard = [
            [LuxuryUI.button("Premium Subscription", "premium", "gold")],
            [LuxuryUI.button("Product Purchase", "product", "silver")]
        ]
        await update.message.reply_text(
            MessageTemplates.welcome(first_name),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_callback(update: Update, context):
    """Handle all callbacks with luxury UI"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    # Select subscription type
    if data in ['premium', 'product']:
        request_type = "Premium Subscription" if data == 'premium' else "Product Purchase"
        update_user(user_id, 'request_type', request_type)
        update_user(user_id, 'current_step', 'name_pending')
        
        selected_text = f"""
{LuxuryUI.EMOJIS['diamond']} <b>{request_type}</b> {LuxuryUI.EMOJIS['diamond']}

{LuxuryUI.EMOJIS['check']} Selection confirmed!

{MessageTemplates.step_header(1, 4, "Personal Information")}
Please enter your <b>full name</b>:
"""
        await query.edit_message_text(selected_text, parse_mode=ParseMode.HTML)
        return
    
    # Select payment
    if data in ['binance', 'easypaisa']:
        update_user(user_id, 'payment_method', data.capitalize())
        
        await query.edit_message_text(
            MessageTemplates.payment_info(data),
            parse_mode=ParseMode.HTML
        )
        return
    
    # Admin: Approve application
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
            
            # Remove buttons and update message
            await query.edit_message_reply_markup(reply_markup=None)
            
            original_text = query.message.text or query.message.caption or ""
            updated_text = original_text + MessageTemplates.action_taken('approved')
            
            if query.message.photo:
                await query.edit_message_caption(caption=updated_text, parse_mode=ParseMode.HTML)
            else:
                await query.edit_message_text(updated_text, parse_mode=ParseMode.HTML)
            
            # Notify user with luxury design
            keyboard = [
                [LuxuryUI.button("Binance Pay", "binance", "gold")],
                [LuxuryUI.button("Easypaisa", "easypaisa", "silver")]
            ]
            
            await context.bot.send_message(
                chat_id=target_id,
                text=f"""
{LuxuryUI.EMOJIS['medal']} <b>APPLICATION APPROVED!</b> {LuxuryUI.EMOJIS['medal']}

{LuxuryUI.EMOJIS['divider']}

Congratulations! You have been approved for membership.

<b>Payment Required:</b> {MEMBERSHIP_FEE}

{LuxuryUI.EMOJIS['info']} Select payment method:
""",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await query.edit_message_text(f"{LuxuryUI.EMOJIS['cross']} Error: {e}")
        return
    
    # Admin: Reject application
    if data.startswith('reject_'):
        try:
            target_id = int(data.split('_')[1])
            context.user_data['reject_id'] = target_id
            
            # Remove buttons
            await query.edit_message_reply_markup(reply_markup=None)
            
            original_text = query.message.text or query.message.caption or ""
            updated_text = original_text + MessageTemplates.action_taken('rejected')
            
            if query.message.photo:
                await query.edit_message_caption(caption=updated_text, parse_mode=ParseMode.HTML)
            else:
                await query.edit_message_text(updated_text, parse_mode=ParseMode.HTML)
            
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"""
{LuxuryUI.EMOJIS['cross']} <b>REJECTION REASON REQUIRED</b>

User ID: <code>{target_id}</code>

Please type the reason for rejection:
"""
            )
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await query.edit_message_text(f"{LuxuryUI.EMOJIS['cross']} Error: {e}")
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
            
            # Remove buttons
            await query.edit_message_reply_markup(reply_markup=None)
            
            original_text = query.message.caption or ""
            updated_text = original_text + MessageTemplates.action_taken('payment_approved')
            
            await query.edit_message_caption(caption=updated_text, parse_mode=ParseMode.HTML)
            
            # Send VIP access to user
            await context.bot.send_message(
                chat_id=target_id,
                text=MessageTemplates.success_access(),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await query.edit_message_text(f"{LuxuryUI.EMOJIS['cross']} Error: {e}")
        return
    
    # Admin: Reject payment
    if data.startswith('rejectpay_'):
        try:
            target_id = int(data.split('_')[1])
            context.user_data['reject_id'] = target_id
            context.user_data['reject_payment'] = True
            
            # Remove buttons
            await query.edit_message_reply_markup(reply_markup=None)
            
            original_text = query.message.caption or ""
            updated_text = original_text + MessageTemplates.action_taken('payment_rejected')
            
            await query.edit_message_caption(caption=updated_text, parse_mode=ParseMode.HTML)
            
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"""
{LuxuryUI.EMOJIS['cross']} <b>PAYMENT REJECTION REASON</b>

User ID: <code>{target_id}</code>

Please type the reason for payment rejection:
"""
            )
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await query.edit_message_text(f"{LuxuryUI.EMOJIS['cross']} Error: {e}")
        return

async def handle_text(update: Update, context):
    """Handle text with luxury validation"""
    user_id = update.effective_user.id
    text = update.message.text
    
    user_data = get_user(user_id)
    if not user_data:
        await update.message.reply_text(
            f"{LuxuryUI.EMOJIS['info']} Please send /start to begin",
            parse_mode=ParseMode.HTML
        )
        return
    
    step = user_data[7]
    
    # Handle name
    if step == 'name_pending':
        if len(text) < 2:
            await update.message.reply_text(
                f"{LuxuryUI.EMOJIS['cross']} Name too short. Please enter full name:",
                parse_mode=ParseMode.HTML
            )
            return
        
        update_user(user_id, 'full_name', text)
        update_user(user_id, 'current_step', 'email_pending')
        
        await update.message.reply_text(
            MessageTemplates.step_header(2, 4, "Contact Details") +
            f"\n{LuxuryUI.EMOJIS['check']} Name: <b>{text}</b>\n\nPlease enter your email:",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Handle email
    if step == 'email_pending':
        if "@" not in text or "." not in text.split('@')[-1]:
            await update.message.reply_text(
                f"{LuxuryUI.EMOJIS['cross']} Invalid email! Try again:",
                parse_mode=ParseMode.HTML
            )
            return
        
        update_user(user_id, 'email', text)
        update_user(user_id, 'current_step', 'proof_pending')
        
        await update.message.reply_text(
            MessageTemplates.step_header(3, 4, "Purchase Verification") +
            f"\n{LuxuryUI.EMOJIS['check']} Email: <b>{text}</b>\n\nUpload proof screenshot:",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Handle WhatsApp
    if step == 'whatsapp_pending':
        clean = re.sub(r'[\s\-\(\)\.]', '', text)
        if not re.match(r'^\+\d{10,15}$', clean):
            await update.message.reply_text(
                f"{LuxuryUI.EMOJIS['cross']} Invalid format! Use: <b>+923001234567</b>",
                parse_mode=ParseMode.HTML
            )
            return
        
        update_user(user_id, 'whatsapp', clean)
        update_user(user_id, 'current_step', 'info_submitted')
        
        await update.message.reply_text(
            f"""
{LuxuryUI.EMOJIS['check']} <b>APPLICATION SUBMITTED!</b> {LuxuryUI.EMOJIS['check']}

{LuxuryUI.EMOJIS['divider']}

Your application is under review.
You will be notified once approved.

{LuxuryUI.EMOJIS['clock']} <i>Thank you for your patience</i>
""",
            parse_mode=ParseMode.HTML
        )
        
        # Send to admin
        keyboard = [
            [
                LuxuryUI.button("Approve", f"approve_{user_id}", "success"),
                LuxuryUI.button("Reject", f"reject_{user_id}", "danger")
            ]
        ]
        
        admin_msg = MessageTemplates.admin_notification(user_data, clean)
        
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
    
    # Handle rejection reason
    if 'reject_id' in context.user_data:
        target_id = context.user_data['reject_id']
        is_payment = context.user_data.get('reject_payment', False)
        
        header = "Payment Rejected" if is_payment else "Application Rejected"
        
        await context.bot.send_message(
            chat_id=target_id,
            text=f"""
{LuxuryUI.EMOJIS['cross']} <b>{header}</b> {LuxuryUI.EMOJIS['cross']}

Reason: <i>{text}</i>

{LuxuryUI.EMOJIS['info']} Contact support if you believe this is an error.
"""
        )
        
        await update.message.reply_text(
            f"{LuxuryUI.EMOJIS['check']} Rejection sent to user {target_id}.",
            parse_mode=ParseMode.HTML
        )
        
        del context.user_data['reject_id']
        if 'reject_payment' in context.user_data:
            del context.user_data['reject_payment']
        return

async def handle_photo(update: Update, context):
    """Handle photos with luxury feedback"""
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
            MessageTemplates.step_header(4, 4, "Final Step") +
            "\n" + LuxuryUI.EMOJIS['check'] + " Proof received!\n\nEnter WhatsApp (+923001234567):",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Payment proof
    if admin_approved == 1 and status == 'payment_pending':
        photo = update.message.photo[-1]
        
        # Check duplicate
        try:
            file = await photo.get_file()
            bytes_data = await file.download_as_bytearray()
            hash_val = hashlib.md5(bytes_data).hexdigest()
        except Exception as e:
            logger.error(f"Error: {e}")
            await update.message.reply_text(
                f"{LuxuryUI.EMOJIS['cross']} Error processing image. Try again.",
                parse_mode=ParseMode.HTML
            )
            return
        
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT 1 FROM screenshots WHERE file_hash = ?", (hash_val,))
        if c.fetchone():
            await update.message.reply_text(
                f"""
{LuxuryUI.EMOJIS['cross']} <b>DUPLICATE DETECTED</b> {LuxuryUI.EMOJIS['cross']}

This screenshot has already been used.
Please send a unique payment proof.
""",
                parse_mode=ParseMode.HTML
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
            f"""
{LuxuryUI.EMOJIS['clock']} <b>PAYMENT RECEIVED</b> {LuxuryUI.EMOJIS['clock']}

{LuxuryUI.EMOJIS['divider']}

Your payment is being verified.
You will receive access within 5-10 minutes.

{LuxuryUI.EMOJIS['info']} Do not send multiple screenshots.
""",
            parse_mode=ParseMode.HTML
        )
        
        # Send to admin
        keyboard = [
            [
                LuxuryUI.button("Verify & Grant Access", f"final_{user_id}", "gold"),
                LuxuryUI.button("Reject Payment", f"rejectpay_{user_id}", "danger")
            ]
        ]
        
        admin_text = MessageTemplates.admin_notification(user_data, None, is_payment=True)
        
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo.file_id,
            caption=admin_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

def main():
    """Run the luxury bot"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("""
    ╔══════════════════════════════════════╗
    ║     👑 LUXURY BOT ACTIVATED 👑       ║
    ╠══════════════════════════════════════╣
    ║  Premium Experience Initialized      ║
    ║  Admin ID: {}                
    ║  Status: ONLINE                      ║
    ╚══════════════════════════════════════╝
    """.format(ADMIN_ID))
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
