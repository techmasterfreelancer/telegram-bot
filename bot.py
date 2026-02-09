import logging
import sqlite3
import hashlib
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ConversationHandler, ContextTypes, filters
from telegram.constants import ParseMode

# ============= YOUR DETAILS HERE =============

BOT_TOKEN = "8535390425:AAGdysiGhg5y82rCLkVi2t2yJGGhCXXlnIY"
ADMIN_ID = 7291034213  # YOUR_TELEGRAM_ID_HERE

# GROUP LINKS
TELEGRAM_GROUP_LINK = "https://t.me/+P8gZuIBH75RiOThk"

# PAYMENT DETAILS
BINANCE_EMAIL = "techmasterfreelancer@gmail.com"
BINANCE_ID = "1129541950"
BINANCE_NETWORK = "TRC20"
WALLET_ADDRESS = "TNzf9V9Jmr2mhq5H8Xa3bLhhB8dwmWdG9B7"

EASYPAYSA_NAME = "Jaffar Ali"
EASYPAYSA_NUMBER = "03486623402"

MEMBERSHIP_FEE = "$5 USD (Lifetime)"

# REMINDER SETTINGS
REMINDER_INTERVAL_HOURS = 24  # Reminder every 24 hours
CHECK_INTERVAL_MINUTES = 60   # Check every hour

# =====================================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============= DATABASE SETUP =============

def init_db():
    conn = sqlite3.connect('bot.db')
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
        created_at TIMESTAMP,
        updated_at TIMESTAMP,
        admin_approved_at TIMESTAMP,
        last_reminder_sent TIMESTAMP,
        reminder_count INTEGER DEFAULT 0
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
    return sqlite3.connect('bot.db')

def get_user_data(user_id):
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
                 (user_id, username, current_step, status, created_at, updated_at, reminder_count) 
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (user_id, username, 'start', 'new', now, now, 0))
    conn.commit()
    conn.close()

def update_user(user_id, field, value):
    conn = get_db()
    c = conn.cursor()
    c.execute(f"UPDATE users SET {field} = ?, updated_at = ? WHERE user_id = ?",
              (value, datetime.now(), user_id))
    conn.commit()
    conn.close()

def update_step(user_id, step):
    update_user(user_id, 'current_step', step)

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

def get_pending_payment_users():
    """Get users where exactly 24, 48, 72... hours have passed since admin approval"""
    conn = get_db()
    c = conn.cursor()
    now = datetime.now()
    
    # Get all payment_pending users
    c.execute('''SELECT user_id, username, full_name, admin_approved_at, 
                 last_reminder_sent, reminder_count 
                 FROM users 
                 WHERE status = 'payment_pending' ''')
    results = c.fetchall()
    conn.close()
    
    users_to_remind = []
    
    for user in results:
        approved_at = user[3]
        if not approved_at:
            continue
            
        # Parse approval time
        try:
            if isinstance(approved_at, str):
                approved_time = datetime.strptime(approved_at, '%Y-%m-%d %H:%M:%S.%f')
            else:
                approved_time = approved_at
        except:
            continue
        
        # Calculate hours since approval
        hours_since_approval = int((now - approved_time).total_seconds() / 3600)
        
        # Check if it's time for reminder (24, 48, 72, 96... hours)
        if hours_since_approval > 0 and hours_since_approval % REMINDER_INTERVAL_HOURS == 0:
            # Check if we already sent reminder in last 30 minutes (to avoid duplicates)
            last_reminder = user[4]
            if last_reminder:
                try:
                    if isinstance(last_reminder, str):
                        last_reminder_time = datetime.strptime(last_reminder, '%Y-%m-%d %H:%M:%S.%f')
                    else:
                        last_reminder_time = last_reminder
                    
                    minutes_since_last_reminder = int((now - last_reminder_time).total_seconds() / 60)
                    
                    # If last reminder was sent less than 30 minutes ago, skip
                    if minutes_since_last_reminder < 30:
                        continue
                except:
                    pass
            
            users_to_remind.append(user)
    
    return users_to_remind

def update_reminder_sent(user_id):
    """Update last reminder time and increment count"""
    conn = get_db()
    c = conn.cursor()
    c.execute('''UPDATE users 
                 SET last_reminder_sent = ?, reminder_count = reminder_count + 1 
                 WHERE user_id = ?''',
              (datetime.now(), user_id))
    conn.commit()
    conn.close()

def set_admin_approved_time(user_id):
    """Set the time when admin approved the application"""
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET admin_approved_at = ? WHERE user_id = ?",
              (datetime.now(), user_id))
    conn.commit()
    conn.close()

# ============= CONVERSATION STATES =============

SELECT_TYPE, GET_NAME, GET_EMAIL, GET_PROOF, GET_WHATSAPP, ADMIN_REVIEW, SELECT_PAYMENT, GET_PAYMENT_PROOF, FINAL_APPROVAL = range(9)

# ============= START COMMAND =============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle start command with resume feature"""
    user = update.effective_user
    user_id = user.id
    username = user.username or "No username"
    
    # Get existing user data
    user_data = get_user_data(user_id)
    
    if not user_data:
        # New user
        create_user(user_id, username)
        await send_welcome(update, user.first_name)
        return SELECT_TYPE
    
    # Existing user - check status
    step = user_data[7]  # current_step
    status = user_data[11]  # status
    reminder_count = user_data[16] if len(user_data) > 16 else 0
    
    # If already approved and active
    if status == 'approved':
        await update.message.reply_text(
            f"✅ *Welcome back {user.first_name}!*\n\n"
            f"You are already approved and have access to the premium groups.\n\n"
            f"🔗 *Telegram Group:*\n{TELEGRAM_GROUP_LINK}\n\n"
            f"📱 *WhatsApp Group:*\n{WHATSAPP_GROUP_LINK}",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    # If info submitted, waiting for admin review (user skipped payment selection)
    if status == 'new' and step == 'proof_submitted':
        await update.message.reply_text(
            f"⏳ *Hello {user.first_name}!*\n\n"
            f"Your information has already been submitted for admin review.\n"
            f"🕐 *Please wait...*\n\n"
            f"Status: *Pending Review*\n"
            f"The admin will review your application and notify you soon.\n\n"
            f"⚠️ *Do not submit again. Please wait for admin response.*",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    # If admin approved but user hasn't paid yet (PAYMENT PENDING REMINDER)
    if status == 'payment_pending':
        keyboard = [
            [InlineKeyboardButton("💰 Binance", callback_data='pay_binance')],
            [InlineKeyboardButton("📱 Easypaisa", callback_data='pay_easypaisa')]
        ]
        
        # Add urgency message if reminder count > 0
        urgency_text = ""
        if reminder_count > 0:
            urgency_text = f"\n⚠️ *Reminder #{reminder_count}:* Your payment is still pending!\n"
        
        await update.message.reply_text(
            f"⏰ *Payment Reminder - {user.first_name}!*{urgency_text}\n\n"
            f"✅ Your submitted information has been *reviewed and approved* by admin!\n\n"
            f"💳 *Status: Payment Pending*\n\n"
            f"💎 *To join the Premium Group, please complete your payment:*\n"
            f"💵 *Fee:* {MEMBERSHIP_FEE}\n\n"
            f"👇 *Select your payment method:*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        return SELECT_PAYMENT
    
    # If payment proof submitted, waiting for verification
    if step == 'payment_submitted':
        await update.message.reply_text(
            f"⏳ *Hello {user.first_name}!*\n\n"
            f"Your payment proof has been submitted to admin.\n"
            f"🕐 *Waiting for verification...*\n\n"
            f"Status: *Payment Verification Pending*\n"
            f"You will receive group links once payment is confirmed.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    # Resume from where left
    if step == 'name_pending':
        await update.message.reply_text(
            f"🔄 *Welcome back {user.first_name}!*\n\n"
            f"📝 *Please enter your full name:*",
            parse_mode=ParseMode.MARKDOWN
        )
        return GET_NAME
    
    if step == 'email_pending':
        await update.message.reply_text(
            f"🔄 *Welcome back {user.first_name}!*\n\n"
            f"✅ Name: *{user_data[2]}*\n\n"
            f"📧 *Please enter your email address:*",
            parse_mode=ParseMode.MARKDOWN
        )
        return GET_EMAIL
    
    if step == 'proof_pending':
        request_type = user_data[5] or "product"
        await update.message.reply_text(
            f"🔄 *Welcome back {user.first_name}!*\n\n"
            f"📸 *You have not sent your {request_type} proof yet.*\n\n"
            f"Please send a clear screenshot:",
            parse_mode=ParseMode.MARKDOWN
        )
        return GET_PROOF
    
    if step == 'whatsapp_pending':
        await update.message.reply_text(
            f"🔄 *Welcome back {user.first_name}!*\n\n"
            f"✅ Name: *{user_data[2]}*\n"
            f"✅ Email: *{user_data[3]}*\n"
            f"✅ Proof received\n\n"
            f"📱 *Please enter your WhatsApp number (with country code):*\n\n"
            f"Example: +923001234567, +14155552671, +447911123456",
            parse_mode=ParseMode.MARKDOWN
        )
        return GET_WHATSAPP
    
    # Default - restart
    await send_welcome(update, user.first_name)
    return SELECT_TYPE

async def send_welcome(update, first_name):
    """Send welcome message"""
    keyboard = [
        [InlineKeyboardButton("💎 Premium Subscription", callback_data='type_premium')],
        [InlineKeyboardButton("🛒 Product Purchase", callback_data='type_product')]
    ]
    
    await update.message.reply_text(
        f"👋 *Welcome {first_name}!*\n\n"
        f"Did you purchase a *Premium Subscription* or a *Product* from my website?\n\n"
        f"👇 *Please select:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

# ============= TYPE SELECTION =============

async def select_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle type selection"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data.split('_')[1]
    request_type = "Premium Subscription" if data == 'premium' else "Product Purchase"
    
    update_user(user_id, 'request_type', request_type)
    update_step(user_id, 'name_pending')
    
    await query.edit_message_text(
        f"✅ *{request_type}* selected!\n\n"
        f"💎 *To join the premium group, we need some information.*\n\n"
        f"📝 *Step 1/4: Please enter your full name:*",
        parse_mode=ParseMode.MARKDOWN
    )
    return GET_NAME

# ============= COLLECT INFO =============

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get full name"""
    user_id = update.effective_user.id
    name = update.message.text
    
    update_user(user_id, 'full_name', name)
    update_step(user_id, 'email_pending')
    
    await update.message.reply_text(
        f"✅ *Name: {name}*\n\n"
        f"📧 *Step 2/4: Please enter your email address:*",
        parse_mode=ParseMode.MARKDOWN
    )
    return GET_EMAIL

async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get email"""
    user_id = update.effective_user.id
    email = update.message.text
    
    # Validate
    if "@" not in email or "." not in email:
        await update.message.reply_text(
            "❌ *Invalid email!* Please enter a valid email address:",
            parse_mode=ParseMode.MARKDOWN
        )
        return GET_EMAIL
    
    update_user(user_id, 'email', email)
    update_step(user_id, 'proof_pending')
    
    # Get request type for message
    user_data = get_user_data(user_id)
    request_type = user_data[5] or "product"
    
    await update.message.reply_text(
        f"✅ *Email: {email}*\n\n"
        f"📸 *Step 3/4: Please send proof/screenshot of your {request_type}:*\n\n"
        f"⚠️ *Image must be clear showing all details*",
        parse_mode=ParseMode.MARKDOWN
    )
    return GET_PROOF

async def get_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get proof screenshot"""
    user_id = update.effective_user.id
    
    if not update.message.photo:
        await update.message.reply_text(
            "❌ *Please send an image!* Send a screenshot:",
            parse_mode=ParseMode.MARKDOWN
        )
        return GET_PROOF
    
    # Save photo
    photo = update.message.photo[-1]
    file_id = photo.file_id
    
    update_user(user_id, 'proof_file_id', file_id)
    update_step(user_id, 'whatsapp_pending')
    
    # Get user data for confirmation
    user_data = get_user_data(user_id)
    
    await update.message.reply_text(
        f"✅ *Proof received!*\n\n"
        f"📱 *Step 4/4: Please enter your WhatsApp number (with country code):*\n\n"
        f"Examples:\n"
        f"🇵🇰 Pakistan: +923001234567\n"
        f"🇺🇸 USA: +14155552671\n"
        f"🇬🇧 UK: +447911123456\n"
        f"🇮🇳 India: +919876543210\n"
        f"🇦🇪 UAE: +971501234567",
        parse_mode=ParseMode.MARKDOWN
    )
    return GET_WHATSAPP

async def get_whatsapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get WhatsApp and submit to admin"""
    user_id = update.effective_user.id
    whatsapp = update.message.text
    
    # Universal WhatsApp validation for all countries
    # Remove spaces, dashes, and common separators
    cleaned_number = whatsapp.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    
    # Check if starts with + and followed by 7-15 digits
    pattern = r'^\+\d{7,15}$'
    if not re.match(pattern, cleaned_number):
        await update.message.reply_text(
            "❌ *Invalid number!* Please enter a valid WhatsApp number with country code:\n\n"
            f"Examples:\n"
            f"🇵🇰 +923001234567\n"
            f"🇺🇸 +14155552671\n"
            f"🇬🇧 +447911123456\n"
            f"🇮🇳 +919876543210\n"
            f"🇦🇪 +971501234567\n"
            f"🇳🇬 +2348012345678\n"
            f"🇧🇩 +8801712345678",
            parse_mode=ParseMode.MARKDOWN
        )
        return GET_WHATSAPP
    
    update_user(user_id, 'whatsapp', cleaned_number)
    update_step(user_id, 'proof_submitted')
    
    # Confirm to user
    await update.message.reply_text(
        "✅ *Your information has been successfully submitted!*\n\n"
        "🕐 *Please wait for admin review...*\n\n"
        "⏳ Your application is under review.\n"
        "🔔 Once approved, you will receive a message for fee payment.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Send to admin
    user_data = get_user_data(user_id)
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f'approve_{user_id}'),
            InlineKeyboardButton("❌ Reject", callback_data=f'reject_{user_id}')
        ]
    ]
    
    caption = f"""
🆕 *NEW APPLICATION*

👤 *User:* @{user_data[1]}
🆔 *ID:* `{user_id}`
📋 *Type:* {user_data[5]}
📝 *Name:* {user_data[2]}
📧 *Email:* {user_data[3]}
📱 *WhatsApp:* {cleaned_number}
⏰ *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M')}

👇 *Please take action:*
    """
    
    # Send proof photo if available
    if user_data[6]:  # proof_file_id
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
    """Admin approves - send fee message"""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split('_')[1])
    
    # Update status and set approval time
    update_user(user_id, 'status', 'payment_pending')
    update_step(user_id, 'payment_pending')
    set_admin_approved_time(user_id)  # Track when admin approved
    
    # Send fee message to user
    keyboard = [
        [InlineKeyboardButton("💰 Binance", callback_data='pay_binance')],
        [InlineKeyboardButton("📱 Easypaisa", callback_data='pay_easypaisa')]
    ]
    
    await context.bot.send_message(
        chat_id=user_id,
        text=f"""
🎉 *APPLICATION APPROVED!*

✅ Admin has *verified* your application!

💎 *To join the Premium Group, Lifetime Fee:*
💵 *{MEMBERSHIP_FEE}*

⚠️ *Important:* You will receive payment reminders every 24 hours until payment is completed.

👇 *Please select your payment method:*
        """,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    
    await query.edit_message_text(
        f"✅ *Approved!*\n\nFee message sent to user `{user_id}`.\n"
        f"⏰ Automatic reminders will be sent every {REMINDER_INTERVAL_HOURS} hours.",
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin rejects application"""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split('_')[1])
    context.user_data['reject_user_id'] = user_id
    
    await query.edit_message_text(
        f"❌ *Rejecting user {user_id}*\n\n"
        f"*Please provide rejection reason (send message):*",
        parse_mode=ParseMode.MARKDOWN
    )
    return ADMIN_REVIEW

async def handle_rejection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle rejection reason"""
    reason = update.message.text
    user_id = context.user_data.get('reject_user_id')
    
    if not user_id:
        await update.message.reply_text("Error!")
        return ConversationHandler.END
    
    # Send to user
    await context.bot.send_message(
        chat_id=user_id,
        text=f"""
❌ *APPLICATION REJECTED*

Your application has been rejected.

*Reason:* {reason}

To apply again, please send /start.
        """,
        parse_mode=ParseMode.MARKDOWN
    )
    
    await update.message.reply_text(f"❌ User {user_id} rejected.")
    return ConversationHandler.END

# ============= PAYMENT FLOW =============

async def show_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show payment details"""
    query = update.callback_query
    await query.answer()
    
    method = query.data.split('_')[1]
    user_id = update.effective_user.id
    
    update_user(user_id, 'payment_method', method.capitalize())
    
    if method == 'binance':
        details = f"""
💰 *BINANCE PAYMENT DETAILS*

📧 *Email:* `{BINANCE_EMAIL}`
🆔 *Binance ID:* `{BINANCE_ID}`
🌐 *Network:* `{BINANCE_NETWORK}`

💵 *Amount:* {MEMBERSHIP_FEE}

✅ *After payment, please send screenshot here.*
        """
    else:
        details = f"""
📱 *EASYPAYSA PAYMENT DETAILS*

👤 *Name:* {EASYPAYSA_NAME}
📞 *Number:* `{EASYPAYSA_NUMBER}`

💵 *Amount:* {MEMBERSHIP_FEE}

✅ *After payment, please send screenshot here.*
        """
    
    await context.bot.send_message(
        chat_id=user_id,
        text=details,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Mark that we're waiting for payment proof
    context.user_data[f'awaiting_payment_{user_id}'] = True
    
    await query.edit_message_text(
        f"✅ *Payment details sent to user {user_id}*",
        parse_mode=ParseMode.MARKDOWN
    )

async def receive_payment_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive payment screenshot"""
    user_id = update.effective_user.id
    
    # Check if user is in payment phase
    user_data = get_user_data(user_id)
    
    if not user_data or user_data[11] != 'payment_pending':
        # Not in payment phase, ignore or handle as new proof
        return
    
    if not update.message.photo:
        await update.message.reply_text(
            "❌ *Please send payment screenshot!*",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Process screenshot
    photo = update.message.photo[-1]
    photo_file = await photo.get_file()
    
    # Check duplicate
    file_bytes = await photo_file.download_as_bytearray()
    image_hash = hashlib.md5(file_bytes).hexdigest()
    
    duplicate = check_duplicate(image_hash)
    if duplicate:
        await update.message.reply_text(
            "🚫 *THIS SCREENSHOT HAS ALREADY BEEN USED!*",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Save
    save_hash(image_hash, user_id)
    
    # Update user
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET payment_file_id = ?, payment_hash = ?, current_step = ? WHERE user_id = ?",
              (photo.file_id, image_hash, 'payment_submitted', user_id))
    conn.commit()
    conn.close()
    
    # Confirm to user
    await update.message.reply_text(
        "⏳ *Payment Screenshot Received!*\n\n"
        "✅ Admin is verifying your payment...\n"
        "🕐 *You will receive group links after approval.*\n\n"
        "⚠️ *Fake screenshots will result in a ban!*",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Send to admin
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve & Send Link", callback_data=f'finallink_{user_id}'),
            InlineKeyboardButton("❌ Reject", callback_data=f'rejectpay_{user_id}')
        ]
    ]
    
    caption = f"""
💰 *NEW PAYMENT RECEIVED*

👤 *User:* @{user_data[1]}
🆔 *ID:* `{user_id}`
📝 *Name:* {user_data[2]}
📧 *Email:* {user_data[3]}
📱 *WhatsApp:* {user_data[4]}
💳 *Method:* {user_data[8]}
⏰ *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M')}

👇 *Please verify:*
    """
    
    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo.file_id,
        caption=caption,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def final_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Final approval - send group links"""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split('_')[1])
    
    # Update status
    update_user(user_id, 'status', 'approved')
    
    # Send links to user
    await context.bot.send_message(
        chat_id=user_id,
        text=f"""
🎉 *PAYMENT APPROVED!*

✅ Your payment has been verified!

🔗 *TELEGRAM GROUP:*
{TELEGRAM_GROUP_LINK}

📱 *WHATSAPP GROUP:*
{WHATSAPP_GROUP_LINK}

⚠️ *Important:*
• Do not share these links
• Follow group rules
• Do not add fake members

🚀 *Welcome to Premium Family!*
        """,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=False
    )
    
    await query.edit_message_text(
        f"✅ *User {user_id} approved!*\nGroup links sent.",
        parse_mode=ParseMode.MARKDOWN
    )

async def reject_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reject payment"""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split('_')[1])
    context.user_data['reject_user_id'] = user_id
    context.user_data['reject_type'] = 'payment'
    
    await query.edit_message_text(
        f"❌ *Rejecting payment {user_id}*\n\n"
        f"*Please provide rejection reason:*",
        parse_mode=ParseMode.MARKDOWN
    )
    return FINAL_APPROVAL

# ============= REMINDER SYSTEM =============

async def send_payment_reminders(context: ContextTypes.DEFAULT_TYPE):
    """Background task to send reminders at exactly 24, 48, 72... hours"""
    try:
        pending_users = get_pending_payment_users()
        
        if not pending_users:
            return
        
        logger.info(f"Sending reminders to {len(pending_users)} users (24h multiples)")
        
        for user in pending_users:
            user_id = user[0]
            username = user[1] or "Unknown"
            full_name = user[2] or "User"
            reminder_count = user[5] if len(user) > 5 else 0
            
            try:
                keyboard = [
                    [InlineKeyboardButton("💰 Binance", callback_data='pay_binance')],
                    [InlineKeyboardButton("📱 Easypaisa", callback_data='pay_easypaisa')]
                ]
                
                # Calculate hours elapsed
                hours_elapsed = (reminder_count + 1) * REMINDER_INTERVAL_HOURS
                
                # Add urgency based on reminder count
                if reminder_count == 0:
                    urgency = "⏰ *24 Hour Reminder*"
                    message = f"Friendly reminder: Your payment is pending."
                elif reminder_count == 1:
                    urgency = "⚠️ *48 Hour Reminder*"
                    message = "Your payment has been pending for 2 days. Please complete soon."
                elif reminder_count == 2:
                    urgency = "🔔 *72 Hour Reminder*"
                    message = "3 days have passed. Complete your payment now to avoid cancellation."
                else:
                    urgency = f"🚨 *{hours_elapsed} Hour Reminder - URGENT!*"
                    message = f"Your payment has been pending for {hours_elapsed//24} days. This is your final reminder!"
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"""
{urgency}

Hello {full_name},

{message}

✅ Your application was *approved by admin* but payment is still pending!

💎 *Premium Group Access Waiting...*
💵 *Fee:* {MEMBERSHIP_FEE}

⏳ *Time elapsed:* {hours_elapsed} hours ({hours_elapsed//24} days)

👇 *Complete your payment now:*
                    """,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.MARKDOWN
                )
                
                # Update reminder sent time
                update_reminder_sent(user_id)
                logger.info(f"Reminder sent to user {user_id} ({username}) - Count: {reminder_count + 1}, Hours: {hours_elapsed}")
                
            except Exception as e:
                logger.error(f"Failed to send reminder to user {user_id}: {e}")
                continue
        
        # Send summary to admin
        if pending_users:
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"""
📊 *Hourly Reminder Summary*

⏰ *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M')}

📋 *Reminders sent:* {len(pending_users)} users
⏱ *Interval:* Every {REMINDER_INTERVAL_HOURS} hours (24h, 48h, 72h...)

💳 *Total pending payments:* Check with /pending command

✅ Reminders continue until payment is received.
                    """,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Failed to send admin summary: {e}")
                
    except Exception as e:
        logger.error(f"Error in reminder task: {e}")

async def check_pending_payments_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to check pending payments"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT user_id, username, full_name, admin_approved_at, reminder_count 
                 FROM users 
                 WHERE status = 'payment_pending' 
                 ORDER BY admin_approved_at''')
    results = c.fetchall()
    conn.close()
    
    if not results:
        await update.message.reply_text("✅ No pending payments!")
        return
    
    message = f"⏳ *Pending Payments ({len(results)} users):*\n\n"
    
    for user in results:
        uid = user[0]
        uname = user[1] or "No username"
        name = user[2] or "Unknown"
        approved_at = user[3]
        reminders = user[4] if len(user) > 4 else 0
        
        # Calculate hours since approval
        try:
            if isinstance(approved_at, str):
                approved_time = datetime.strptime(approved_at, '%Y-%m-%d %H:%M:%S.%f')
            else:
                approved_time = approved_at
            hours_ago = int((datetime.now() - approved_time).total_seconds() / 3600)
            days = hours_ago // 24
        except:
            hours_ago = "Unknown"
            days = "Unknown"
        
        message += f"👤 @{uname} (ID: `{uid}`)\n"
        message += f"   Name: {name}\n"
        message += f"   Reminders sent: {reminders}\n"
        message += f"   Pending for: {days} days ({hours_ago} hours)\n\n"
    
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

# ============= CANCEL =============

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel"""
    await update.message.reply_text(
        "❌ Cancelled.\nTo start again, send /start."
    )
    return ConversationHandler.END

# ============= MAIN =============

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Main conversation
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECT_TYPE: [CallbackQueryHandler(select_type, pattern='^type_')],
            GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            GET_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
            GET_PROOF: [MessageHandler(filters.PHOTO, get_proof)],
            GET_WHATSAPP: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_whatsapp)],
            ADMIN_REVIEW: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_rejection)],
            FINAL_APPROVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_rejection)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(conv_handler)
    
    # Callbacks
    application.add_handler(CallbackQueryHandler(admin_approve, pattern='^approve_'))
    application.add_handler(CallbackQueryHandler(admin_reject, pattern='^reject_'))
    application.add_handler(CallbackQueryHandler(show_payment_details, pattern='^pay_'))
    application.add_handler(CallbackQueryHandler(final_approve, pattern='^finallink_'))
    application.add_handler(CallbackQueryHandler(reject_payment, pattern='^rejectpay_'))
    
    # Admin commands
    application.add_handler(CommandHandler("pending", check_pending_payments_command))
    
    # Payment proof handler
    application.add_handler(MessageHandler(filters.PHOTO, receive_payment_proof))
    
    # Setup scheduler for reminders
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_payment_reminders,
        IntervalTrigger(minutes=CHECK_INTERVAL_MINUTES),
        args=[application],
        id='payment_reminder_job',
        name='Payment Reminder Job',
        replace_existing=True
    )
    scheduler.start()
    
    print("🤖 Bot is running...")
    print(f"⏰ Payment reminders: Every {REMINDER_INTERVAL_HOURS} hours (24h, 48h, 72h...)")
    print(f"🔍 Checking every {CHECK_INTERVAL_MINUTES} minutes")
    
    application.run_polling()

if __name__ == "__main__":
    main()
