"""
Premium Support Bot - Professional Telegram Bot
Complete working code with admin panel and user flow
"""

import logging
import sqlite3
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8535390425:AAE-K_QBPRw7e23GoWnGzCISz7T6pjpBLjQ"
ADMIN_IDS = [7291034213]  # Your Telegram ID
TELEGRAM_GROUP_LINK = "https://t.me/+P8gZuIBH75RiOThk"

# Payment Details
BINANCE_EMAIL = "techmasterfreelancer@gmail.com"
BINANCE_ID = "1129541950"
EASYPAYSA_NAME = "Jaffar Ali"
EASYPAYSA_NUMBER = "03486623402"
MEMBERSHIP_FEE = "$5 USD (Lifetime)"

# Database setup
DB_FILE = 'premium_bot.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            email TEXT,
            phone TEXT,
            purchase_type TEXT,
            proof_photo_id TEXT,
            payment_photo_id TEXT,
            status TEXT DEFAULT 'pending_info',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Admin actions log
    c.execute('''
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            user_id INTEGER,
            action TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# States for ConversationHandler
SELECT_PURCHASE, FULL_NAME, EMAIL, UPLOAD_PROOF, WHATSAPP_NUMBER = range(5)

# Payment details dictionary
PAYMENT_DETAILS = {
    'binance': {
        'title': '💰 Binance Payment',
        'details': f'''*Binance Pay Details:*

📧 *Email:* `{BINANCE_EMAIL}`
🆔 *Binance ID:* `{BINANCE_ID}`

💵 *Amount:* {MEMBERSHIP_FEE}

*Note:* Please send exact amount. Include your Telegram username in memo.'''
    },
    'easypaisa': {
        'title': '📱 Easypaisa Payment',
        'details': f'''*Easypaisa Account Details:*

👤 *Account Name:* {EASYPAYSA_NAME}
📞 *Account Number:* `{EASYPAYSA_NUMBER}`

💵 *Amount:* Rs. 1,400 (Equivalent to $5 USD)
*Note:* Please send screenshot with your name visible.'''
    }
}

# ==================== DATABASE FUNCTIONS ====================

def get_db_connection():
    return sqlite3.connect(DB_FILE)

def save_user(user_id, username=None):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT OR IGNORE INTO users (user_id, username) 
        VALUES (?, ?)
    ''', (user_id, username))
    conn.commit()
    conn.close()

def update_user(user_id, **kwargs):
    conn = get_db_connection()
    c = conn.cursor()
    
    for key, value in kwargs.items():
        c.execute(f'UPDATE users SET {key} = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?', 
                  (value, user_id))
    
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def get_all_pending_users():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE status = ?', ('pending_review',))
    users = c.fetchall()
    conn.close()
    return users

def get_pending_payments():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE status = ?', ('pending_payment_verification',))
    users = c.fetchall()
    conn.close()
    return users

def log_admin_action(admin_id, user_id, action):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO admin_logs (admin_id, user_id, action) VALUES (?, ?, ?)',
              (admin_id, user_id, action))
    conn.commit()
    conn.close()

# ==================== USER COMMANDS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - Welcome message and purchase selection"""
    user = update.effective_user
    save_user(user.id, user.username)
    
    # Reset any existing conversation data
    context.user_data.clear()
    
    # Check if user already has pending or active application
    existing_user = get_user(user.id)
    if existing_user and existing_user[8] in ['pending_review', 'approved_pending_payment', 'pending_payment_verification']:
        await update.message.reply_text(
            "⏳ *You already have an application in progress.*\n\n"
            "Please wait for admin response or contact support.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    if existing_user and existing_user[8] == 'active_member':
        await update.message.reply_text(
            "✅ *You are already a premium member!*\n\n"
            f"🔗 *Join Community:* {TELEGRAM_GROUP_LINK}",
            parse_mode='Markdown',
            disable_web_page_preview=False
        )
        return ConversationHandler.END
    
    welcome_text = f"""🎉 *Welcome to Premium Support Bot*

👤 User: *{user.first_name}*

Please select what you purchased from our website:"""
    
    keyboard = [
        [
            InlineKeyboardButton("📅 Premium Subscription", callback_data='subscription'),
            InlineKeyboardButton("🛍️ Product Purchase", callback_data='product')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    return SELECT_PURCHASE

async def select_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle purchase type selection"""
    query = update.callback_query
    await query.answer()
    
    purchase_type = query.data
    context.user_data['purchase_type'] = purchase_type
    
    # Map for display text
    type_display = {
        'subscription': 'Premium Subscription',
        'product': 'Product Purchase'
    }
    
    await query.edit_message_text(
        f"✅ *You selected: {type_display[purchase_type]}*\n\n"
        f"Now we will collect some information to verify your purchase and add you to our premium community.",
        parse_mode='Markdown'
    )
    
    # Step 1: Ask for full name
    await query.message.reply_text(
        "*Step 1 of 4 – Personal Information*\n\n"
        "Please enter your *full name* as per your ID.\n"
        "_Example: Muhammad Ahmad Khan_",
        parse_mode='Markdown'
    )
    
    return FULL_NAME

async def get_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get user's full name"""
    full_name = update.message.text
    context.user_data['full_name'] = full_name
    user = update.effective_user
    
    await update.message.reply_text(
        f"✅ Thank you *{full_name}*!\n\n"
        f"*Step 2 of 4 – Contact Information*\n\n"
        f"Please enter your *email address*.\n"
        f"_Example: yourname@gmail.com_\n\n"
        f"⚠️ *Important:* Please use the same Gmail you registered with on our website.\n"
        f"Do not use any other email address.",
        parse_mode='Markdown'
    )
    
    return EMAIL

async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get user's email"""
    email = update.message.text
    context.user_data['email'] = email
    
    purchase_type = context.user_data.get('purchase_type', 'subscription')
    proof_text = "Premium Subscription" if purchase_type == 'subscription' else "Product Purchase"
    
    await update.message.reply_text(
        f"✅ *Email saved successfully.*\n\n"
        f"*Step 3 of 4 – Purchase Verification*\n\n"
        f"Please upload a *clear screenshot* of your *{proof_text}* purchase.\n\n"
        f"📸 *Requirements:*\n"
        f"• Upload clear and readable screenshot\n"
        f"• Screenshot must show transaction details\n"
        f"• Fake or edited screenshot will result in *permanent ban*",
        parse_mode='Markdown'
    )
    
    return UPLOAD_PROOF

async def get_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle proof screenshot upload"""
    if not update.message.photo:
        await update.message.reply_text(
            "❌ Please upload a *photo/screenshot*, not a document or text.\n"
            "Try again with a clear image.",
            parse_mode='Markdown'
        )
        return UPLOAD_PROOF
    
    # Get the largest photo (best quality)
    photo = update.message.photo[-1]
    context.user_data['proof_photo_id'] = photo.file_id
    
    await update.message.reply_text(
        f"✅ *Proof received!*\n\n"
        f"*Step 4 of 4 – WhatsApp Number*\n\n"
        f"Please enter your *WhatsApp number* with country code.\n"
        f"_Example: +92 312 3456789_",
        parse_mode='Markdown'
    )
    
    return WHATSAPP_NUMBER

async def get_whatsapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get WhatsApp number and complete application"""
    phone = update.message.text
    user = update.effective_user
    
    # Save all data to database
    update_user(
        user.id,
        full_name=context.user_data.get('full_name'),
        email=context.user_data.get('email'),
        phone=phone,
        purchase_type=context.user_data.get('purchase_type'),
        proof_photo_id=context.user_data.get('proof_photo_id'),
        status='pending_review'
    )
    
    # Send confirmation to user
    confirmation_text = f"""✅ *Application Submitted Successfully*

Your information has been sent to *Admin Team*.

📋 *What happens next:*
• Admin will review your application within *24 hours*
• You will receive approval notification here
• Then you can complete payment to join

⏳ *Application Status:* Pending Review

⚠️ Please do not submit multiple applications.
Wait for official notification from *Premium Support Bot / Tech Master Freelancing*."""

    await update.message.reply_text(confirmation_text, parse_mode='Markdown')
    
    # Notify admins
    await notify_admins_new_application(context, user.id)
    
    return ConversationHandler.END

async def notify_admins_new_application(context, user_id):
    """Send notification to all admins about new application"""
    user = get_user(user_id)
    if not user:
        return
    
    user_data = {
        'user_id': user[0],
        'username': user[1],
        'full_name': user[2],
        'email': user[3],
        'phone': user[4],
        'purchase_type': user[5],
        'proof_photo_id': user[6]
    }
    
    admin_message = f"""🆕 *New Application Received*

👤 *Name:* {user_data['full_name']}
📧 *Email:* {user_data['email']}
📱 *WhatsApp:* {user_data['phone']}
🛒 *Purchase Type:* {user_data['purchase_type']}
🆔 *User ID:* `{user_data['user_id']}`
👤 *Username:* @{user_data['username'] if user_data['username'] else 'N/A'}

📸 *Proof of Purchase:* Attached below

Use /applications to view all pending applications."""

    for admin_id in ADMIN_IDS:
        try:
            # Send text message
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_message,
                parse_mode='Markdown'
            )
            # Send proof photo
            if user_data['proof_photo_id']:
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=user_data['proof_photo_id'],
                    caption="📸 Proof of Purchase"
                )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")

# ==================== PAYMENT FLOW ====================

async def send_payment_request(context, user_id):
    """Send payment request to approved user"""
    benefits = """🌟 *Community Benefits:*
• Weekly live class (Sunday 10 PM Pakistan Time)
• Full premium support
• Growth opportunity
• Lifetime access
• Direct access to Tech Master Freelancing team"""

    keyboard = [
        [
            InlineKeyboardButton("💰 Binance", callback_data=f'pay_binance_{user_id}'),
            InlineKeyboardButton("📱 Easypaisa", callback_data=f'pay_easypaisa_{user_id}')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"""✅ *Your information has been reviewed and approved by Admin.*

To join Premium Community, you need to pay *{MEMBERSHIP_FEE}*.

{benefits}

Please select your payment method:""",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Failed to send payment request to {user_id}: {e}")

async def handle_payment_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment method selection"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    method = data[1]
    user_id = int(data[2])
    
    # Only allow the actual user to select payment
    if query.from_user.id != user_id:
        await query.answer("❌ This is not for you!", show_alert=True)
        return
    
    payment_info = PAYMENT_DETAILS.get(method)
    
    keyboard = [[InlineKeyboardButton("✅ I have paid - Upload Screenshot", callback_data=f'upload_payment_{user_id}')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"{payment_info['title']}\n\n"
        f"{payment_info['details']}\n\n"
        f"⚠️ *After payment, click the button below to upload screenshot.*\n"
        f"Fake screenshot will result in *permanent ban*.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def request_payment_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Request user to upload payment proof"""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split('_')[2])
    
    if query.from_user.id != user_id:
        await query.answer("❌ This is not for you!", show_alert=True)
        return
    
    await query.edit_message_text(
        "📸 *Please upload your payment screenshot now.*\n\n"
        "Make sure it's clear and shows:\n"
        "• Transaction ID/Reference\n"
        "• Amount sent\n"
        "• Date and time\n\n"
        "Type /cancel to cancel.",
        parse_mode='Markdown'
    )
    
    # Store state for payment upload
    context.user_data['awaiting_payment_proof'] = True
    context.user_data['payment_user_id'] = user_id

async def handle_payment_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment proof upload"""
    user = update.effective_user
    
    # Check if user is in payment upload mode
    if not context.user_data.get('awaiting_payment_proof'):
        return
    
    if not update.message.photo:
        await update.message.reply_text("❌ Please upload a photo/screenshot of your payment.")
        return
    
    photo = update.message.photo[-1]
    
    # Update user status
    update_user(user.id, payment_photo_id=photo.file_id, status='pending_payment_verification')
    
    # Clear the flag
    context.user_data['awaiting_payment_proof'] = False
    
    await update.message.reply_text(
        "✅ *Payment proof sent to admin for verification.*\n\n"
        "Please wait while we verify your payment. You will be notified within 24 hours.\n\n"
        "⏳ *Status:* Awaiting Admin Verification",
        parse_mode='Markdown'
    )
    
    # Notify admins
    await notify_admins_payment(context, user.id, photo.file_id)

async def notify_admins_payment(context, user_id, photo_id):
    """Notify admins about new payment proof"""
    user = get_user(user_id)
    if not user:
        return
    
    admin_message = f"""💰 *New Payment Received for Verification*

👤 *Name:* {user[2]}
📧 *Email:* {user[3]}
📱 *WhatsApp:* {user[4]}
🆔 *User ID:* `{user[0]}`
👤 *Username:* @{user[1] if user[1] else 'N/A'}

📸 *Payment Screenshot:* Attached below

Use /payments to view all pending payment verifications."""

    keyboard = [
        [
            InlineKeyboardButton("✅ Verify & Send Link", callback_data=f'approve_payment_{user_id}'),
            InlineKeyboardButton("❌ Reject Payment", callback_data=f'reject_payment_{user_id}')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=photo_id,
                caption=admin_message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")

# ==================== ADMIN COMMANDS ====================

async def admin_applications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all pending applications to admin"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized!")
        return
    
    pending = get_all_pending_users()
    
    if not pending:
        await update.message.reply_text("📭 No pending applications.")
        return
    
    await update.message.reply_text(f"📋 *Pending Applications: {len(pending)}*", parse_mode='Markdown')
    
    for user_data in pending:
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f'approve_info_{user_data[0]}'),
                InlineKeyboardButton("❌ Reject", callback_data=f'reject_info_{user_data[0]}')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        app_text = f"""👤 *Application #{user_data[0]}*

*Name:* {user_data[2]}
*Email:* {user_data[3]}
*Phone:* {user_data[4]}
*Type:* {user_data[5]}
*Username:* @{user_data[1] if user_data[1] else 'N/A'}
*Date:* {user_data[8]}"""

        try:
            await update.message.reply_photo(
                photo=user_data[6],
                caption=app_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error sending application: {e}")
            await update.message.reply_text(
                f"{app_text}\n\n[Photo failed to load]",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

async def admin_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all pending payment verifications"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized!")
        return
    
    pending = get_pending_payments()
    
    if not pending:
        await update.message.reply_text("📭 No pending payment verifications.")
        return
    
    await update.message.reply_text(f"💰 *Pending Payments: {len(pending)}*", parse_mode='Markdown')
    
    for user_data in pending:
        keyboard = [
            [
                InlineKeyboardButton("✅ Verify & Send Link", callback_data=f'approve_payment_{user_data[0]}'),
                InlineKeyboardButton("❌ Reject Payment", callback_data=f'reject_payment_{user_data[0]}')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        pay_text = f"""💳 *Payment Verification #{user_data[0]}*

*Name:* {user_data[2]}
*Email:* {user_data[3]}
*Phone:* {user_data[4]}
*Type:* {user_data[5]}
*Username:* @{user_data[1] if user_data[1] else 'N/A'}
*Date:* {user_data[8]}"""

        try:
            await update.message.reply_photo(
                photo=user_data[7],  # payment_photo_id
                caption=pay_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error sending payment: {e}")

async def handle_admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin approve/reject decisions"""
    query = update.callback_query
    await query.answer()
    
    admin = update.effective_user
    
    if admin.id not in ADMIN_IDS:
        await query.answer("❌ Unauthorized!", show_alert=True)
        return
    
    data = query.data.split('_')
    action = data[0]  # approve or reject
    stage = data[1]  # info or payment
    user_id = int(data[2])
    
    if action == 'approve':
        if stage == 'info':
            # Approve info, move to payment
            update_user(user_id, status='approved_pending_payment')
            log_admin_action(admin.id, user_id, 'approved_info')
            
            await query.edit_message_caption(
                caption=f"{query.message.caption}\n\n✅ *APPROVED by Admin*\n⏳ Payment request sent to user.",
                parse_mode='Markdown'
            )
            
            # Send payment request to user
            await send_payment_request(context, user_id)
            
        elif stage == 'payment':
            # Approve payment, send community link
            update_user(user_id, status='active_member')
            log_admin_action(admin.id, user_id, 'approved_payment')
            
            # Send welcome message with link to user
            welcome_msg = f"""🎉 *Congratulations! Your payment has been verified.*

Welcome to *Premium Community*! 🚀

🔗 *Join Now:* {TELEGRAM_GROUP_LINK}

📜 *Community Rules:*
• Be respectful to all members
• No spam or self-promotion without permission
• Keep discussions relevant to tech/freelancing
• Share knowledge and help others grow
• Maintain confidentiality of premium content
• Attend weekly live class (Sunday 10 PM PKT)

⚡ *Your Membership:* {MEMBERSHIP_FEE} - Lifetime Access

Welcome aboard! 🎯"""
            
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=welcome_msg,
                    parse_mode='Markdown',
                    disable_web_page_preview=False
                )
            except Exception as e:
                logger.error(f"Failed to send welcome message: {e}")
            
            await query.edit_message_caption(
                caption=f"{query.message.caption}\n\n✅ *PAYMENT VERIFIED*\n🎉 User added to community!",
                parse_mode='Markdown'
            )
    
    elif action == 'reject':
        if stage == 'info':
            update_user(user_id, status='rejected_info')
            log_admin_action(admin.id, user_id, 'rejected_info')
            
            # Send rejection to user
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="""❌ *Application Rejected*

Your application has been rejected due to:
• Invalid information provided
• Fake or edited purchase proof
• Email mismatch with website records

⚠️ *Warning:* Attempting to submit fake information again will result in *permanent ban* from all our services.

Contact @TechMasterSupport if you believe this is a mistake.""",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send rejection: {e}")
            
            await query.edit_message_caption(
                caption=f"{query.message.caption}\n\n❌ *REJECTED by Admin*",
                parse_mode='Markdown'
            )
        
        elif stage == 'payment':
            update_user(user_id, status='rejected_payment')
            log_admin_action(admin.id, user_id, 'rejected_payment')
            
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="""❌ *Payment Verification Failed*

Your payment proof was rejected due to:
• Invalid or fake screenshot
• Unclear image (unreadable)
• Transaction not found in our records
• Amount mismatch

⚠️ *Warning:* Fake payment attempts will result in *permanent ban*.

Please submit correct payment proof by typing /start""",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send payment rejection: {e}")
            
            await query.edit_message_caption(
                caption=f"{query.message.caption}\n\n❌ *PAYMENT REJECTED*",
                parse_mode='Markdown'
            )

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics to admin"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    conn = get_db_connection()
    c = conn.cursor()
    
    stats = {}
    for status in ['pending_review', 'approved_pending_payment', 'pending_payment_verification', 'active_member', 'rejected_info', 'rejected_payment']:
        c.execute('SELECT COUNT(*) FROM users WHERE status = ?', (status,))
        stats[status] = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM users')
    total = c.fetchone()[0]
    
    # Today's applications
    c.execute("SELECT COUNT(*) FROM users WHERE date(created_at) = date('now')")
    today = c.fetchone()[0]
    
    conn.close()
    
    stats_text = f"""📊 *Bot Statistics*

👥 *Total Users:* {total}
📈 *Today:* {today} new applications

⏳ *Pending Review:* {stats['pending_review']}
💰 *Awaiting Payment:* {stats['approved_pending_payment']}
🔍 *Payment Verification:* {stats['pending_payment_verification']}
✅ *Active Members:* {stats['active_member']}
❌ *Rejected Apps:* {stats['rejected_info']}
❌ *Rejected Payments:* {stats['rejected_payment']}"""

    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin commands help"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        return
    
    help_text = """🔐 *Admin Commands*

/applications - View pending applications
/payments - View pending payment verifications
/stats - View bot statistics
/help - Show this help message

*How to use:*
1. User submits application → You get notification
2. Click ✅ Approve or ❌ Reject on the photo
3. If approved, user gets payment request
4. User pays and uploads proof → You get notification
5. Verify payment and send group link

*Contact:* @TechMasterFreelancer"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

# ==================== ERROR HANDLING ====================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel conversation"""
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Process cancelled. Type /start to begin again.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ An error occurred. Please type /start to try again."
        )

# ==================== MAIN FUNCTION ====================

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Conversation handler for user flow
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECT_PURCHASE: [CallbackQueryHandler(select_purchase, pattern='^(subscription|product)$')],
            FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_full_name)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
            UPLOAD_PROOF: [MessageHandler(filters.PHOTO, get_proof)],
            WHATSAPP_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_whatsapp)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    application.add_handler(conv_handler)
    
    # Admin commands
    application.add_handler(CommandHandler('applications', admin_applications))
    application.add_handler(CommandHandler('payments', admin_payments))
    application.add_handler(CommandHandler('stats', admin_stats))
    application.add_handler(CommandHandler('help', admin_help))
    
    # Callback handlers for admin decisions
    application.add_handler(CallbackQueryHandler(handle_admin_decision, pattern='^(approve|reject)_(info|payment)_\d+$'))
    
    # Payment flow callbacks
    application.add_handler(CallbackQueryHandler(handle_payment_selection, pattern='^pay_(binance|easypaisa)_\d+$'))
    application.add_handler(CallbackQueryHandler(request_payment_upload, pattern='^upload_payment_\d+$'))
    
    # Payment proof handler (outside conversation)
    application.add_handler(MessageHandler(
        filters.PHOTO, 
        handle_payment_proof
    ))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    print("🤖 Premium Support Bot is running...")
    print(f"👤 Admin ID: {ADMIN_IDS[0]}")
    print(f"💾 Database: {DB_FILE}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
