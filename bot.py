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

BOT_TOKEN = "8535390425:AAF67T7kjqxYxmjQTFhCH_l_6RnT_aB5frg"
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

# ============= BOT FUNCTIONS =============

async def start(update: Update, context):
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name

    user_data = get_user(user_id)

    # EXACT WELCOME MESSAGE FROM SCREENSHOT 1
    welcome_text = """🎉 <b>Welcome to Premium Support Bot!</b> 🎉

Hello {first_name}! 👋

This is your gateway to exclusive premium content and live learning sessions.

📚 <b>What You'll Get:</b>
• Full support for all purchases
• Weekly live sessions (Sunday 10 PM PK)
• Instant updates on new content
• Lifetime access to premium community

👇 <b>Please select what you purchased from our website:</b>""".format(first_name=first_name)

    if not user_data:
        create_user(user_id, user.username or "No username")

        keyboard = [
            [InlineKeyboardButton("💎 Premium Subscription", callback_data='premium')],
            [InlineKeyboardButton("🛒 Product Purchase", callback_data='product')]
        ]

        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    status = user_data[11]  # status column
    admin_approved = user_data[12]  # admin_approved column
    step = user_data[7]  # current_step column

    # Already completed
    if status == 'completed':
        completed_text = f"""🎉 <b>PAYMENT VERIFIED!</b> 🎉

✅ Your payment has been confirmed!

🔗 <b>TELEGRAM GROUP:</b>
{TELEGRAM_GROUP_LINK}

📱 <b>WhatsApp Group:</b>
{WHATSAPP_GROUP_LINK}

🔒 <b>Important:</b> Do not share these links!
🚀 Welcome to the Premium Family!"""
        await update.message.reply_text(completed_text, parse_mode=ParseMode.HTML)
        return

    # Approved, waiting for payment
    if admin_approved == 1 and status == 'payment_pending':
        payment_reminder = f"""🎉 <b>CONGRATULATIONS!</b> 🎉

✅ Your application has been <b>APPROVED</b>!

💰 <b>To complete your registration, please pay:</b>
<b>{MEMBERSHIP_FEE}</b>

Select your payment method:"""
        keyboard = [
            [InlineKeyboardButton("💰 Binance Pay", callback_data='binance')],
            [InlineKeyboardButton("📱 Easypaisa", callback_data='easypaisa')]
        ]

        await update.message.reply_text(
            payment_reminder,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Pending review
    if step == 'info_submitted':
        pending_text = """🎊 <b>Application Submitted Successfully!</b> 🎊

━━━━━━━━━━━━━━━━━━
✅ <b>What happens next?</b>
━━━━━━━━━━━━━━━━━━

⏳ <b>Step 1:</b> Admin reviews your application
Estimated time: 2-24 hours

📧 <b>Step 2:</b> You'll receive approval notification here

💳 <b>Step 3:</b> Complete payment to join premium group

🔗 <b>Step 4:</b> Get instant access to all resources

━━━━━━━━━━━━━━━━━━
📊 <b>Your Status:</b> ⏳ PENDING REVIEW
━━━━━━━━━━━━━━━━━━

🔔 You'll be notified as soon as admin approves!

⚠️ <b>Please do not submit multiple applications.</b>"""
        await update.message.reply_text(pending_text, parse_mode=ParseMode.HTML)
        return

    # Payment verification pending
    if step == 'payment_submitted':
        await update.message.reply_text(
            "⏰ <b>Payment Verification</b>

"
            "Your payment screenshot has been submitted and is being verified.
"
            "You will receive access links once confirmed.",
            parse_mode=ParseMode.HTML
        )
        return

    # Resume incomplete steps
    if step == 'name_pending':
        await update.message.reply_text(
            "👤 <b>Step 1 of 4: Personal Information</b>

"
            "Please enter your <b>full name</b> (as on your ID):",
            parse_mode=ParseMode.HTML
        )
    elif step == 'email_pending':
        await update.message.reply_text(
            f"✅ <b>Name saved!</b>

"
            f"📧 <b>Step 2 of 4:</b> Please enter your email address:",
            parse_mode=ParseMode.HTML
        )
    elif step == 'proof_pending':
        # Check request type for appropriate message
        req_type = user_data[5] or "Premium Subscription"
        if "Product" in req_type:
            proof_text = """✅ <b>Email Saved!</b> ✅

━━━━━━━━━━━━━━━━━━
📸 <b>Step 3 of 4: Purchase Proof</b>
━━━━━━━━━━━━━━━━━━

Please upload <b>ONE</b> of the following:

📱 <b>For Product Purchase:</b>
• Screenshot of purchase confirmation
• Payment receipt/invoice
• Order confirmation email screenshot

✅ <b>Acceptable formats:</b> Image (JPG, PNG)

⚠️ <b>Requirements:</b>
• Clear and readable
• Shows purchase details
• Shows date and amount
• Your name/email visible (if possible)"""
        else:
            proof_text = """✅ <b>Email Saved!</b> ✅

━━━━━━━━━━━━━━━━━━
📸 <b>Step 3 of 4: Purchase Proof</b>
━━━━━━━━━━━━━━━━━━

Please upload <b>ONE</b> of the following:

📱 <b>For Premium Subscription:</b>
• Screenshot of purchase confirmation
• Payment receipt/invoice
• Order confirmation email screenshot

✅ <b>Acceptable formats:</b> Image (JPG, PNG)

⚠️ <b>Requirements:</b>
• Clear and readable
• Shows purchase details
• Shows date and amount
• Your name/email visible (if possible)

❌ <b>Blurry or fake screenshots = Permanent ban</b>"""
        await update.message.reply_text(proof_text, parse_mode=ParseMode.HTML)
    elif step == 'whatsapp_pending':
        await update.message.reply_text(
            "✅ <b>Proof received!</b>

"
            "📱 <b>Step 4 of 4:</b> Please enter your WhatsApp number
"
            "<i>Format: +923001234567</i>",
            parse_mode=ParseMode.HTML
        )
    else:
        # Restart
        keyboard = [
            [InlineKeyboardButton("💎 Premium Subscription", callback_data='premium')],
            [InlineKeyboardButton("🛒 Product Purchase", callback_data='product')]
        ]
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_callback(update: Update, context):
    """Handle all callback queries - ADMIN LOGIC UNCHANGED"""
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

        selected_text = f"""✅ <b>{request_type}</b> selected!

👤 <b>Step 1 of 4: Personal Information</b>

Please enter your <b>full name</b> (as on your ID):"""
        await query.edit_message_text(selected_text, parse_mode=ParseMode.HTML)
        return

    # Select payment method
    if data in ['binance', 'easypaisa']:
        update_user(user_id, 'payment_method', data.capitalize())

        if data == 'binance':
            payment_text = f"""💰 <b>BINANCE PAYMENT DETAILS</b>

┌─ Transfer Information ─┐
📧 Email: <code>{BINANCE_EMAIL}</code>
🆔 ID: <code>{BINANCE_ID}</code>
🔗 Network: <code>{BINANCE_NETWORK}</code>
💰 Amount: <b>{MEMBERSHIP_FEE}</b>
└─────────────────────┘

⚠️ <i>Send exact amount to avoid delays</i>

✅ After payment, send screenshot here for verification."""
        else:
            payment_text = f"""📱 <b>EASYPAYSA PAYMENT DETAILS</b>

┌─ Transfer Information ─┐
👤 Account Name: <b>{EASYPAYSA_NAME}</b>
📱 Number: <code>{EASYPAYSA_NUMBER}</code>
💰 Amount: <b>{MEMBERSHIP_FEE}</b>
└─────────────────────┘

⚠️ <i>Send exact amount to avoid delays</i>

✅ After payment, send screenshot here for verification."""

        await query.edit_message_text(payment_text, parse_mode=ParseMode.HTML)
        return

    # Admin: Approve initial application - LOGIC UNCHANGED
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
            updated_text = f"{original_text}\n\n✅ <b>ACTION TAKEN: APPROVED</b> ✅\n<i>User has been notified to complete payment.</i>"

            if query.message.photo:
                await query.edit_message_caption(caption=updated_text, parse_mode=ParseMode.HTML)
            else:
                await query.edit_message_text(updated_text, parse_mode=ParseMode.HTML)

            # Notify user
            keyboard = [
                [InlineKeyboardButton("💰 Binance Pay", callback_data='binance')],
                [InlineKeyboardButton("📱 Easypaisa", callback_data='easypaisa')]
            ]

            await context.bot.send_message(
                chat_id=target_id,
                text=f"""🎉 <b>CONGRATULATIONS!</b> 🎉

✅ Your application has been <b>APPROVED</b>!

💰 To complete your registration, please pay:
<b>{MEMBERSHIP_FEE}</b>

Select your payment method:""",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

            logger.info(f"Admin approved user {target_id}")

        except Exception as e:
            logger.error(f"Error in approve: {e}")
            await query.edit_message_text(f"❌ Error: {e}")
        return

    # Admin: Reject initial application - LOGIC UNCHANGED
    if data.startswith('reject_'):
        try:
            target_id = int(data.split('_')[1])
            context.user_data['reject_id'] = target_id

            # Remove buttons from admin message
            await query.edit_message_reply_markup(reply_markup=None)

            original_text = query.message.text or query.message.caption or ""
            updated_text = f"{original_text}\n\n❌ <b>ACTION TAKEN: REJECTED</b> ❌\n<i>Waiting for rejection reason...</i>"

            if query.message.photo:
                await query.edit_message_caption(caption=updated_text, parse_mode=ParseMode.HTML)
            else:
                await query.edit_message_text(updated_text, parse_mode=ParseMode.HTML)

            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"❌ <b>Rejection Process</b>\n\nUser ID: <code>{target_id}</code>\n\nPlease type the reason for rejection:"
            )

        except Exception as e:
            logger.error(f"Error in reject: {e}")
            await query.edit_message_text(f"❌ Error: {e}")
        return

    # Admin: Final approve after payment - LOGIC UNCHANGED
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
            updated_text = f"{original_text}\n\n✅ <b>ACTION TAKEN: PAYMENT VERIFIED & LINKS SENT</b> ✅\n<i>User has been granted full access.</i>"

            await query.edit_message_caption(caption=updated_text, parse_mode=ParseMode.HTML)

            # Send access to user
            await context.bot.send_message(
                chat_id=target_id,
                text=f"""🎉 <b>PAYMENT VERIFIED!</b> 🎉

✅ Your payment has been confirmed!

🔗 <b>TELEGRAM GROUP:</b>
{TELEGRAM_GROUP_LINK}

📱 <b>WhatsApp Group:</b>
{WHATSAPP_GROUP_LINK}

🔒 <b>Important:</b> Do not share these links!
🚀 Welcome to the Premium Family!"""
            )

            logger.info(f"Admin finalized approval for user {target_id}")

        except Exception as e:
            logger.error(f"Error in final approve: {e}")
            await query.edit_message_text(f"❌ Error: {e}")
        return

    # Admin: Reject payment - LOGIC UNCHANGED
    if data.startswith('rejectpay_'):
        try:
            target_id = int(data.split('_')[1])
            context.user_data['reject_id'] = target_id
            context.user_data['reject_payment'] = True

            # Remove buttons from admin message
            await query.edit_message_reply_markup(reply_markup=None)

            original_text = query.message.caption or ""
            updated_text = f"{original_text}\n\n❌ <b>ACTION TAKEN: REJECTING PAYMENT</b> ❌\n<i>Waiting for rejection reason...</i>"

            await query.edit_message_caption(caption=updated_text, parse_mode=ParseMode.HTML)

            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"❌ <b>Payment Rejection</b>\n\nUser ID: <code>{target_id}</code>\n\nPlease type the reason for payment rejection:"
            )

        except Exception as e:
            logger.error(f"Error in reject payment: {e}")
            await query.edit_message_text(f"❌ Error: {e}")
        return

async def handle_text(update: Update, context):
    """Handle text messages with validation - ADMIN NOTIFICATION FIXED"""
    user_id = update.effective_user.id
    text = update.message.text

    user_data = get_user(user_id)
    if not user_data:
        await update.message.reply_text(
            "⚠️ Please send /start to begin registration.",
            parse_mode=ParseMode.HTML
        )
        return

    step = user_data[7]  # current_step

    # Handle full name
    if step == 'name_pending':
        if len(text) < 2:
            await update.message.reply_text(
                "❌ Name too short. Please enter your full name:",
                parse_mode=ParseMode.HTML
            )
            return

        update_user(user_id, 'full_name', text)
        update_user(user_id, 'current_step', 'email_pending')

        await update.message.reply_text(
            f"✅ <b>Name saved: {text}</b>

"
            f"📧 <b>Step 2 of 4:</b> Please enter your email address:
"
            f"<i>Example: yourname@gmail.com</i>",
            parse_mode=ParseMode.HTML
        )
        return

    # Handle email - EXACT TEXT FROM SCREENSHOT 3
    if step == 'email_pending':
        if "@" not in text or "." not in text.split('@')[-1]:
            await update.message.reply_text(
                "❌ Invalid email format!\n"
                "Please enter a valid email (example: user@email.com):",
                parse_mode=ParseMode.HTML
            )
            return

        update_user(user_id, 'email', text)
        update_user(user_id, 'current_step', 'proof_pending')

        # Get request type to show appropriate message
        req_type = user_data[5] or "Premium Subscription"

        if "Product" in req_type:
            email_saved_text = """✅ <b>Email Saved!</b> ✅

━━━━━━━━━━━━━━━━━━
📸 <b>Step 3 of 4: Purchase Proof</b>
━━━━━━━━━━━━━━━━━━

Please upload <b>ONE</b> of the following:

📱 <b>For Product Purchase:</b>
• Screenshot of purchase confirmation
• Payment receipt/invoice
• Order confirmation email screenshot

✅ <b>Acceptable formats:</b> Image (JPG, PNG)

⚠️ <b>Requirements:</b>
• Clear and readable
• Shows purchase details
• Shows date and amount
• Your name/email visible (if possible)"""
        else:
            email_saved_text = """✅ <b>Email Saved!</b> ✅

━━━━━━━━━━━━━━━━━━
📸 <b>Step 3 of 4: Purchase Proof</b>
━━━━━━━━━━━━━━━━━━

Please upload <b>ONE</b> of the following:

📱 <b>For Premium Subscription:</b>
• Screenshot of purchase confirmation
• Payment receipt/invoice
• Order confirmation email screenshot

✅ <b>Acceptable formats:</b> Image (JPG, PNG)

⚠️ <b>Requirements:</b>
• Clear and readable
• Shows purchase details
• Shows date and amount
• Your name/email visible (if possible)

❌ <b>Blurry or fake screenshots = Permanent ban</b>"""

        await update.message.reply_text(email_saved_text, parse_mode=ParseMode.HTML)
        return

    # Handle WhatsApp - FIXED ADMIN NOTIFICATION
    if step == 'whatsapp_pending':
        clean = re.sub(r'[\s\-\(\)\.]', '', text)
        if not re.match(r'^\+\d{10,15}$', clean):
            await update.message.reply_text(
                "❌ Invalid format!\n"
                "Please use international format: <b>+923001234567</b>",
                parse_mode=ParseMode.HTML
            )
            return

        update_user(user_id, 'whatsapp', clean)
        update_user(user_id, 'current_step', 'info_submitted')

        # EXACT SUCCESS MESSAGE FROM SCREENSHOT 2
        success_text = """🎊 <b>Application Submitted Successfully!</b> 🎊

━━━━━━━━━━━━━━━━━━
✅ <b>What happens next?</b>
━━━━━━━━━━━━━━━━━━

⏳ <b>Step 1:</b> Admin reviews your application
Estimated time: 2-24 hours

📧 <b>Step 2:</b> You'll receive approval notification here

💳 <b>Step 3:</b> Complete payment to join premium group

🔗 <b>Step 4:</b> Get instant access to all resources

━━━━━━━━━━━━━━━━━━
📊 <b>Your Status:</b> ⏳ PENDING REVIEW
━━━━━━━━━━━━━━━━━━

🔔 You'll be notified as soon as admin approves!

⚠️ <b>Please do not submit multiple applications.</b>"""

        await update.message.reply_text(success_text, parse_mode=ParseMode.HTML)

        # REFRESH USER DATA to get latest values including name, email, proof
        fresh_user_data = get_user(user_id)

        # FIXED: Properly extract all user data with None checks
        username = fresh_user_data[1] or "N/A"
        full_name = fresh_user_data[2] or "Not provided"
        email = fresh_user_data[3] or "Not provided"
        request_type = fresh_user_data[5] or "Unknown"
        proof_file_id = fresh_user_data[6]  # This is the proof photo

        # Send to admin with action buttons - EXACT SAME LOGIC AS BEFORE
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f'approve_{user_id}'),
                InlineKeyboardButton("❌ Reject", callback_data=f'reject_{user_id}')
            ]
        ]

        admin_text = f"""⭐ <b>NEW APPLICATION</b> ⭐

👤 User: @{username}
🆔 ID: <code>{user_id}</code>
👤 Name: <b>{full_name}</b>
📧 Email: <b>{email}</b>
📱 WhatsApp: <code>{clean}</code>
ℹ️ Type: <b>{request_type}</b>

⏰ Received: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

        try:
            if proof_file_id:  # If proof photo exists
                await context.bot.send_photo(
                    chat_id=ADMIN_ID,
                    photo=proof_file_id,
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
            logger.info(f"Admin notification sent for user {user_id}")
        except Exception as e:
            logger.error(f"Error sending admin notification: {e}")
            # Try to notify admin about the error
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"⚠️ Error sending notification for user {user_id}: {str(e)}"
                )
            except:
                pass
        return

    # Handle rejection reason - LOGIC UNCHANGED
    if 'reject_id' in context.user_data:
        target_id = context.user_data['reject_id']
        is_payment = context.user_data.get('reject_payment', False)

        reason_header = "Payment Rejected" if is_payment else "Application Rejected"

        await context.bot.send_message(
            chat_id=target_id,
            text=f"""❌ <b>{reason_header}</b>

Reason: <i>{text}</i>

If you believe this is an error, please contact support."""
        )

        await update.message.reply_text(
            f"✅ Rejection sent to user {target_id}.",
            parse_mode=ParseMode.HTML
        )

        del context.user_data['reject_id']
        if 'reject_payment' in context.user_data:
            del context.user_data['reject_payment']
        return

async def handle_photo(update: Update, context):
    """Handle photo uploads - LOGIC UNCHANGED"""
    user_id = update.effective_user.id
    user_data = get_user(user_id)

    if not user_data:
        return

    step = user_data[7]  # current_step
    admin_approved = user_data[12]  # admin_approved
    status = user_data[11]  # status

    # First proof (purchase proof)
    if step == 'proof_pending':
        file_id = update.message.photo[-1].file_id
        update_user(user_id, 'proof_file_id', file_id)
        update_user(user_id, 'current_step', 'whatsapp_pending')

        await update.message.reply_text(
            "✅ <b>Proof received!</b>\n\n"
            "📱 <b>Step 4 of 4:</b> Please enter your WhatsApp number\n"
            "<i>Format: +923001234567</i>",
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
                "❌ Error processing image. Please try again.",
                parse_mode=ParseMode.HTML
            )
            return

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT 1 FROM screenshots WHERE file_hash = ?", (hash_val,))
        if c.fetchone():
            await update.message.reply_text(
                "❌ <b>Duplicate Screenshot Detected!</b>\n\n"
                "This screenshot has already been used. Please send a unique payment proof.",
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
            "⏳ <b>Payment Received!</b>\n\n"
            "Your payment is being verified by our team.\n"
            "You will receive access links shortly.",
            parse_mode=ParseMode.HTML
        )

        # Send to admin for final verification - LOGIC UNCHANGED
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve & Send Links", callback_data=f'final_{user_id}'),
                InlineKeyboardButton("❌ Reject Payment", callback_data=f'rejectpay_{user_id}')
            ]
        ]

        admin_text = f"""💰 <b>PAYMENT VERIFICATION REQUIRED</b>

👤 User: @{user_data[1] or 'N/A'}
🆔 ID: <code>{user_id}</code>
👤 Name: <b>{user_data[2] or 'N/A'}</b>
💰 Method: <b>{user_data[8] or 'N/A'}</b>
⏰ Submitted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

⚠️ Please verify payment and approve/reject:"""

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
