"""
Premium Support Bot - Professional Telegram Bot for User Onboarding
Created for Railway.app Deployment
Author: Professional Developer
"""

import os
import logging
import asyncio
from datetime import datetime
from typing import Dict, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)
import psycopg2
from psycopg2.extras import RealDictCursor

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration from Environment Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8535390425:AAH4RF9v6k8H6fMQeXr_OQ6JuB7PV8gvgLs")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "7291034213"))
TELEGRAM_GROUP_LINK = os.environ.get("TELEGRAM_GROUP_LINK", "https://t.me/+P8gZuIBH75RiOThk")
BINANCE_EMAIL = os.environ.get("BINANCE_EMAIL", "techmasterfreelancer@gmail.com")
BINANCE_ID = os.environ.get("BINANCE_ID", "1129541950")
EASYPAYSA_NAME = os.environ.get("EASYPAYSA_NAME", "Jaffar Ali")
EASYPAYSA_NUMBER = os.environ.get("EASYPAYSA_NUMBER", "03486623402")
MEMBERSHIP_FEE = os.environ.get("MEMBERSHIP_FEE", "$5 USD (Lifetime)")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")
PORT = int(os.environ.get("PORT", "8080"))

# Conversation States
(
    SELECTING_TYPE, FULL_NAME, EMAIL_VERIFICATION, 
    PURCHASE_PROOF, WHATSAPP_NUMBER, PAYMENT_METHOD, PAYMENT_PROOF
) = range(7)

# Database Connection
def get_db_connection():
    """Create database connection"""
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    else:
        # Fallback to SQLite-like behavior with PostgreSQL
        return psycopg2.connect(
            host="localhost",
            database="premium_bot",
            user="postgres",
            password="password",
            cursor_factory=RealDictCursor
        )

def init_database():
    """Initialize database tables"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                full_name VARCHAR(255),
                email VARCHAR(255),
                whatsapp_number VARCHAR(50),
                purchase_type VARCHAR(50),
                purchase_proof TEXT,
                payment_method VARCHAR(50),
                payment_proof TEXT,
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Admin actions log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_actions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(id),
                action VARCHAR(50),
                performed_by BIGINT,
                performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

def get_user(telegram_id: int) -> Optional[Dict]:
    """Get user by telegram ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return dict(user) if user else None
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return None

def create_user(telegram_id: int, username: str, first_name: str, last_name: str) -> bool:
    """Create new user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (telegram_id, username, first_name, last_name)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (telegram_id) DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                updated_at = CURRENT_TIMESTAMP
        """, (telegram_id, username, first_name, last_name))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return False

def update_user(telegram_id: int, **kwargs) -> bool:
    """Update user fields"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        set_clause = ", ".join([f"{key} = %s" for key in kwargs.keys()])
        values = list(kwargs.values()) + [telegram_id]

        cursor.execute(f"""
            UPDATE users 
            SET {set_clause}, updated_at = CURRENT_TIMESTAMP 
            WHERE telegram_id = %s
        """, values)

        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return False

def log_admin_action(user_id: int, action: str, performed_by: int):
    """Log admin action"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO admin_actions (user_id, action, performed_by)
            VALUES (%s, %s, %s)
        """, (user_id, action, performed_by))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error logging admin action: {e}")

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation"""
    user = update.effective_user

    # Create/update user in database
    create_user(user.id, user.username, user.first_name, user.last_name)

    # Welcome message with professional formatting
    welcome_text = f"""
<b>🌟 Welcome to Premium Support Bot</b>

Hello <b>{user.first_name}</b>! 👋

Aap ne hamari website se kya purchase kiya hai? <b>Subscription</b> ya koi <b>Product</b>?

Hum aap ko <b>full support</b> provide karenge. Jo community hum aap ke saath share karne wale hain us mein aap ko:

✅ <b>Weekly live session</b> (Sunday 10 PM Pakistan Time)
✅ <b>Instant updates</b> inside community  
✅ <b>Lifetime access</b> to premium community

<i>Please select what you purchased from our website:</i>
• Agar <b>subscription</b> buy ki hai to "📦 Subscription" select karein.
• Agar <b>product</b> purchase kiya hai to "🛍️ Product" select karein.
"""

    keyboard = [
        [InlineKeyboardButton("📦 Subscription", callback_data="subscription")],
        [InlineKeyboardButton("🛍️ Product", callback_data="product")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML")
    return SELECTING_TYPE

# Handle Purchase Type Selection
async def select_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle subscription/product selection"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    purchase_type = query.data

    # Update user in database
    update_user(user.id, purchase_type=purchase_type)

    if purchase_type == "subscription":
        message = f"""
<b>🎉 Excellent Choice!</b>

You selected: <b>Premium Subscription</b>

<b>🔐 Verification Process</b>
We will verify your purchase and add you to your premium community.

<b>Step 1 – Personal Details</b>
Please enter your <b>full name</b> as per your ID card.

<i>Example: Muhammad Ali Khan</i>
"""
    else:
        message = f"""
<b>🎉 Excellent Choice!</b>

You selected: <b>Product Purchase</b>

<b>🔐 Verification Process</b>
We will verify your purchase and provide you with product support.

<b>Step 1 – Personal Details</b>
Please enter your <b>full name</b> as per your ID card.

<i>Example: Muhammad Ali Khan</i>
"""

    await query.edit_message_text(message, parse_mode="HTML")
    return FULL_NAME

# Handle Full Name
async def receive_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive and save full name"""
    user = update.effective_user
    full_name = update.message.text.strip()

    if len(full_name) < 3:
        await update.message.reply_text(
            "⚠️ <b>Invalid Name!</b>\nPlease enter your full name correctly (at least 3 characters).",
            parse_mode="HTML"
        )
        return FULL_NAME

    # Update user
    update_user(user.id, full_name=full_name)

    message = f"""
<b>✅ Thank you, {full_name}!</b>

<b>Step 2 – Email Verification</b>

<b>⚠️ Important Instructions:</b>
• Please enter the <b>same email address</b> that you used for registration on our website and login to your account.
• This is <b>required</b> for verification process.
• <b>Do not use different email.</b>

<i>Example: yourname@gmail.com</i>
"""

    await update.message.reply_text(message, parse_mode="HTML")
    return EMAIL_VERIFICATION

# Handle Email
async def receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive and save email"""
    user = update.effective_user
    email = update.message.text.strip()

    # Basic email validation
    if "@" not in email or "." not in email:
        await update.message.reply_text(
            "⚠️ <b>Invalid Email Format!</b>\nPlease enter a valid email address.",
            parse_mode="HTML"
        )
        return EMAIL_VERIFICATION

    # Update user
    update_user(user.id, email=email)

    message = f"""
<b>✅ Email saved!</b>

Thanks for providing your email: <code>{email}</code>

<b>Step 3 – Purchase Proof</b>

Please <b>upload one of the following</b>:

For premium subscription:
📸 <b>Screenshot</b> of your purchase <b>OR</b>
📄 <b>Invoice</b>

<b>📋 Requirements:</b>
✓ Clear and readable
✓ Must show purchase details

<b>⚠️ Warning:</b>
<blockquote>Blur or fake screenshot will permanently ban you from the community.</blockquote>

<i>Please upload your screenshot now...</i>
"""

    await update.message.reply_text(message, parse_mode="HTML")
    return PURCHASE_PROOF

# Handle Purchase Proof (Photo)
async def receive_purchase_proof(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive purchase proof screenshot"""
    user = update.effective_user

    if not update.message.photo:
        await update.message.reply_text(
            "⚠️ <b>Please upload a photo/screenshot!</b>\nSend image file only.",
            parse_mode="HTML"
        )
        return PURCHASE_PROOF

    # Get the largest photo
    photo = update.message.photo[-1]
    file_id = photo.file_id

    # Update user with proof
    update_user(user.id, purchase_proof=file_id)

    message = f"""
<b>✅ Screenshot received!</b>

<b>Step 4 – WhatsApp Number</b>

Please provide your <b>WhatsApp number</b> with country code.

<i>Example: +923001234567</i>

<b>📱 This will be used for:</b>
• Community updates
• Important announcements  
• Direct communication if needed
"""

    await update.message.reply_text(message, parse_mode="HTML")
    return WHATSAPP_NUMBER

# Handle WhatsApp Number
async def receive_whatsapp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive WhatsApp number and complete application"""
    user = update.effective_user
    whatsapp = update.message.text.strip()

    # Basic validation for phone number
    if len(whatsapp) < 10 or not whatsapp.startswith("+"):
        await update.message.reply_text(
            "⚠️ <b>Invalid Format!</b>\nPlease enter number with country code.\nExample: +923001234567",
            parse_mode="HTML"
        )
        return WHATSAPP_NUMBER

    # Update user
    update_user(user.id, whatsapp_number=whatsapp)

    # Get user data for summary
    user_data = get_user(user.id)

    # Send confirmation to user
    confirmation_message = f"""
<b>🎊 Application Submitted Successfully!</b>

<b>📋 What happens next:</b>

<b>Step 1</b> – Admin will review your application
<i>⏱ Estimated time: 2 hours to 24 hours</i>

<b>Step 2</b> – You will receive approval notification here

<b>Step 3</b> – Complete payment to join premium group

<b>Step 4</b> – Get instant access to all resources

<b>📊 Status:</b> <code>⏳ Pending Review</code>

<b>⚠️ Please do not submit multiple applications.</b>

<i>We will notify you once admin reviews your application.</i>
"""

    await update.message.reply_text(confirmation_message, parse_mode="HTML")

    # Send notification to ADMIN with Approve/Reject buttons
    admin_message = f"""
<b>🔔 NEW APPLICATION RECEIVED</b>

<b>👤 User Details:</b>
<b>Name:</b> {user_data.get('full_name', 'N/A')}
<b>Username:</b> @{user_data.get('username', 'N/A')}
<b>Telegram ID:</b> <code>{user.id}</code>
<b>Email:</b> <code>{user_data.get('email', 'N/A')}</code>
<b>WhatsApp:</b> <code>{whatsapp}</code>
<b>Purchase Type:</b> {user_data.get('purchase_type', 'N/A').title()}
<b>Submitted:</b> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

<b>📸 Purchase Proof:</b> Screenshot attached above

<b>⚡ Action Required:</b> Please review and take action.
"""

    # Admin keyboard with one-time buttons
    admin_keyboard = [
        [
            InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{user.id}"),
            InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{user.id}")
        ]
    ]
    admin_reply_markup = InlineKeyboardMarkup(admin_keyboard)

    # Send photo to admin first, then message with buttons
    try:
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=user_data.get('purchase_proof'),
            caption=admin_message,
            reply_markup=admin_reply_markup,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error sending to admin: {e}")
        # Try without photo if failed
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_message,
            reply_markup=admin_reply_markup,
            parse_mode="HTML"
        )

    return ConversationHandler.END

# Admin Approve Action
async def approve_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin approval"""
    query = update.callback_query
    await query.answer()

    # Extract user ID from callback data
    callback_data = query.data
    user_id = int(callback_data.split("_")[1])

    # Check if already processed
    if "processed" in callback_data:
        await query.edit_message_text(
            "<b>⚠️ This application has already been processed.</b>",
            parse_mode="HTML"
        )
        return

    # Update user status
    update_user(user_id, status="approved")

    # Log admin action
    user_data = get_user(user_id)
    if user_data:
        log_admin_action(user_data.get('id'), 'approved', ADMIN_ID)

    # Send payment instructions to user
    payment_message = f"""
<b>🎉 Congratulations! Your Application is APPROVED!</b>

<b>💳 Community Joining Fee: {MEMBERSHIP_FEE}</b>

Please select your preferred payment method:
"""

    payment_keyboard = [
        [InlineKeyboardButton("💚 Easypaisa", callback_data=f"pay_easypaisa_{user_id}")],
        [InlineKeyboardButton("🟡 Binance", callback_data=f"pay_binance_{user_id}")]
    ]
    payment_markup = InlineKeyboardMarkup(payment_keyboard)

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=payment_message,
            reply_markup=payment_markup,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error sending payment message to user: {e}")

    # Update admin message to remove buttons and show processed
    await query.edit_message_text(
        f"{query.message.text}\n\n<b>✅ APPROVED by Admin</b>\n<i>Payment request sent to user.</i>",
        parse_mode="HTML"
    )

# Admin Reject Action
async def reject_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin rejection"""
    query = update.callback_query
    await query.answer()

    callback_data = query.data
    user_id = int(callback_data.split("_")[1])

    # Update user status
    update_user(user_id, status="rejected")

    # Log admin action
    user_data = get_user(user_id)
    if user_data:
        log_admin_action(user_data.get('id'), 'rejected', ADMIN_ID)

    # Send rejection message to user
    reject_message = f"""
<b>❌ Application Rejected</b>

We regret to inform you that your application has been <b>rejected</b>.

<b>Possible reasons:</b>
• Invalid or unclear purchase proof
• Information mismatch
• Multiple applications detected
• Violation of community rules

<b>📞 Contact Support:</b>
If you believe this is a mistake, please contact our support team with valid documentation.

<b>⚠️ Warning:</b> Attempting to submit false information may result in permanent ban.
"""

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=reject_message,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error sending rejection to user: {e}")

    # Update admin message
    await query.edit_message_text(
        f"{query.message.text}\n\n<b>❌ REJECTED by Admin</b>",
        parse_mode="HTML"
    )

# Handle Payment Method Selection
async def select_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show payment details based on selection"""
    query = update.callback_query
    await query.answer()

    callback_data = query.data
    parts = callback_data.split("_")
    method = parts[1]
    user_id = int(parts[2])

    if method == "easypaisa":
        payment_details = f"""
<b>💚 Easypaisa Payment Details</b>

<b>Account Name:</b> <code>{EASYPAYSA_NAME}</code>
<b>Account Number:</b> <code>{EASYPAYSA_NUMBER}</code>
<b>Amount:</b> <code>{MEMBERSHIP_FEE}</code>

<b>📸 Next Step:</b>
After making payment, please <b>upload screenshot</b> of your payment confirmation here.

<b>⚠️ Important:</b>
• Payment must be from your own account
• Screenshot must clearly show transaction ID
• Fake screenshots will result in permanent ban
"""
    else:  # binance
        payment_details = f"""
<b>🟡 Binance Payment Details</b>

<b>Email:</b> <code>{BINANCE_EMAIL}</code>
<b>User ID:</b> <code>{BINANCE_ID}</code>
<b>Amount:</b> <code>{MEMBERSHIP_FEE}</code>

<b>📸 Next Step:</b>
After making payment, please <b>upload screenshot</b> of your payment confirmation here.

<b>⚠️ Important:</b>
• Send payment via Binance Pay
• Include your Telegram username in memo
• Screenshot must show transaction details
• Fake screenshots will result in permanent ban
"""

    # Update user with payment method
    update_user(user_id, payment_method=method)

    await query.edit_message_text(payment_details, parse_mode="HTML")

    # Store state that we're waiting for payment proof
    context.user_data['awaiting_payment_proof'] = True
    context.user_data['payment_user_id'] = user_id

# Handle Payment Proof
async def receive_payment_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive payment screenshot from user"""
    user = update.effective_user

    if not update.message.photo:
        await update.message.reply_text(
            "⚠️ <b>Please upload payment screenshot as photo!</b>",
            parse_mode="HTML"
        )
        return

    photo = update.message.photo[-1]
    file_id = photo.file_id

    # Update user with payment proof
    update_user(user.id, payment_proof=file_id, status="payment_pending")

    # Confirm to user
    await update.message.reply_text(
        "<b>⏳ Payment proof received!</b>\n\nAdmin will verify your payment shortly. You will receive community link once verified.",
        parse_mode="HTML"
    )

    # Notify admin
    user_data = get_user(user.id)
    admin_payment_msg = f"""
<b>💰 PAYMENT PROOF RECEIVED</b>

<b>From User:</b>
<b>Name:</b> {user_data.get('full_name', 'N/A')}
<b>Username:</b> @{user_data.get('username', 'N/A')}
<b>Telegram ID:</b> <code>{user.id}</code>
<b>Payment Method:</b> {user_data.get('payment_method', 'N/A').title()}
<b>Amount:</b> {MEMBERSHIP_FEE}

<b>📸 Payment Screenshot:</b> Attached above

<b>⚡ Action Required:</b> Verify payment and grant access.
"""

    payment_keyboard = [
        [
            InlineKeyboardButton("✅ PAYMENT VERIFIED - GRANT ACCESS", callback_data=f"payment_approve_{user.id}"),
            InlineKeyboardButton("❌ REJECT PAYMENT", callback_data=f"payment_reject_{user.id}")
        ]
    ]
    payment_markup = InlineKeyboardMarkup(payment_keyboard)

    try:
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=file_id,
            caption=admin_payment_msg,
            reply_markup=payment_markup,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error sending payment proof to admin: {e}")

# Handle Payment Approval
async def approve_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Grant access after payment verification"""
    query = update.callback_query
    await query.answer()

    callback_data = query.data
    user_id = int(callback_data.split("_")[2])

    # Update user status
    update_user(user_id, status="completed")

    # Log action
    user_data = get_user(user_id)
    if user_data:
        log_admin_action(user_data.get('id'), 'payment_approved', ADMIN_ID)

    # Send community link to user
    success_message = f"""
<b>🎊 PAYMENT VERIFIED - WELCOME TO PREMIUM COMMUNITY!</b>

<b>✅ Your Status:</b> <code>VERIFIED MEMBER</code>

<b>🔗 Community Access Link:</b>
{TELEGRAM_GROUP_LINK}

<b>📋 Community Rules & Restrictions:</b>

<b>✓ DO's:</b>
✓ Respect all members and admins
✓ Share knowledge and help others
✓ Attend weekly live sessions (Sunday 10 PM PKT)
✓ Use proper language (Urdu/English allowed)
✓ Share relevant content only

<b>✗ DON'Ts:</b>
✗ No spamming or advertising
✗ No sharing of personal information publicly
✗ No abusive language or harassment
✗ No sharing of illegal/pirated content
✗ No political or religious debates
✗ No DM spam to other members

<b>⚠️ Violation of rules will result in:</b>
• 1st Warning
• 2nd Temporary mute
• 3rd Permanent ban without refund

<b>🎁 Your Benefits:</b>
• Lifetime access to premium community
• Weekly live sessions with experts
• Instant updates and announcements
• Direct support from admin team
• Exclusive resources and content

<b>📞 Need Help?</b>
Contact admin anytime through this bot.

<b>🌟 Welcome aboard! 🌟</b>
"""

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=success_message,
            parse_mode="HTML",
            disable_web_page_preview=False
        )
    except Exception as e:
        logger.error(f"Error sending community link: {e}")

    # Update admin message
    await query.edit_message_text(
        f"{query.message.text}\n\n<b>✅ PAYMENT VERIFIED & ACCESS GRANTED</b>",
        parse_mode="HTML"
    )

# Handle Payment Rejection
async def reject_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reject payment proof"""
    query = update.callback_query
    await query.answer()

    callback_data = query.data
    user_id = int(callback_data.split("_")[2])

    # Update user status back to approved (so they can retry)
    update_user(user_id, status="approved")

    # Notify user
    retry_message = f"""
<b>❌ Payment Verification Failed</b>

Your payment proof was <b>rejected</b>.

<b>Possible reasons:</b>
• Screenshot unclear or edited
• Transaction not found
• Amount mismatch
• Payment not received

<b>🔄 Next Steps:</b>
Please make the payment again using correct details and upload clear screenshot.

Payment details have been resent to you. Use /start to begin payment process again.
"""

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=retry_message,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error sending payment rejection: {e}")

    # Update admin message
    await query.edit_message_text(
        f"{query.message.text}\n\n<b>❌ PAYMENT REJECTED - User notified to retry</b>",
        parse_mode="HTML"
    )

# Cancel Command
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel conversation"""
    await update.message.reply_text(
        "<b>❌ Process cancelled.</b>\n\nSend /start to begin again.",
        parse_mode="HTML"
    )
    return ConversationHandler.END

# Admin Stats Command
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin statistics"""
    user = update.effective_user

    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ <b>Unauthorized access!</b>", parse_mode="HTML")
        return

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get counts
        cursor.execute("SELECT COUNT(*) as total FROM users")
        total_users = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as pending FROM users WHERE status = 'pending'")
        pending = cursor.fetchone()['pending']

        cursor.execute("SELECT COUNT(*) as approved FROM users WHERE status = 'approved'")
        approved = cursor.fetchone()['approved']

        cursor.execute("SELECT COUNT(*) as completed FROM users WHERE status = 'completed'")
        completed = cursor.fetchone()['completed']

        cursor.execute("SELECT COUNT(*) as rejected FROM users WHERE status = 'rejected'")
        rejected = cursor.fetchone()['rejected']

        cursor.close()
        conn.close()

        stats_text = f"""
<b>📊 BOT STATISTICS</b>

<b>👥 Total Users:</b> <code>{total_users}</code>
<b>⏳ Pending Review:</b> <code>{pending}</code>
<b>✅ Approved (Awaiting Payment):</b> <code>{approved}</code>
<b>🎉 Completed (Paid):</b> <code>{completed}</code>
<b>❌ Rejected:</b> <code>{rejected}</code>

<i>Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</i>
"""
        await update.message.reply_text(stats_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        await update.message.reply_text("⚠️ Error fetching statistics", parse_mode="HTML")

# Error Handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Update {update} caused error {context.error}")

    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ <b>An error occurred!</b>\nPlease try again or contact support.",
            parse_mode="HTML"
        )

# Main Function
def main():
    """Start the bot"""
    # Initialize database
    init_database()

    # Create application
    application = Application.builder().token(BOT_TOKEN).build()

    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECTING_TYPE: [CallbackQueryHandler(select_type, pattern="^(subscription|product)$")],
            FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_full_name)],
            EMAIL_VERIFICATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_email)],
            PURCHASE_PROOF: [MessageHandler(filters.PHOTO, receive_purchase_proof)],
            WHATSAPP_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_whatsapp)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("stats", stats))

    # Callback handlers for admin actions
    application.add_handler(CallbackQueryHandler(approve_user, pattern="^approve_\d+$"))
    application.add_handler(CallbackQueryHandler(reject_user, pattern="^reject_\d+$"))
    application.add_handler(CallbackQueryHandler(select_payment_method, pattern="^pay_(easypaisa|binance)_\d+$"))
    application.add_handler(CallbackQueryHandler(approve_payment, pattern="^payment_approve_\d+$"))
    application.add_handler(CallbackQueryHandler(reject_payment, pattern="^payment_reject_\d+$"))

    # Payment proof handler (outside conversation)
    application.add_handler(MessageHandler(
        filters.PHOTO & filters.User(lambda u: get_user(u.id) and get_user(u.id).get('status') == 'approved'),
        receive_payment_proof
    ))

    # Error handler
    application.add_error_handler(error_handler)

    # Set bot commands
    application.bot.set_my_commands([
        BotCommand("start", "Start application process"),
        BotCommand("stats", "View statistics (Admin only)"),
        BotCommand("cancel", "Cancel current process")
    ])

    # Start bot
    if WEBHOOK_URL:
        # Webhook mode (for Railway)
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=WEBHOOK_URL,
            secret_token="premium_bot_secret"
        )
    else:
        # Polling mode (for local testing)
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
