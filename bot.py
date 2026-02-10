import logging
import sqlite3
import hashlib
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ConversationHandler, ContextTypes, filters
from telegram.constants import ParseMode

# ============= YOUR DETAILS HERE =============

BOT_TOKEN = "8535390425:AAF67T7kjqxYxmjQTFhCH_l_6RnT_aB5frg"
ADMIN_ID = 7291034213  # YOUR_TELEGRAM_ID_HERE

# GROUP LINKS
TELEGRAM_GROUP_LINK = "https://https://t.me/+P8gZuIBH75RiOThk"

# PAYMENT DETAILS
BINANCE_EMAIL = "techmasterfreelancer@gmail.com"
BINANCE_ID = "1129541950"
BINANCE_NETWORK = "TRC20"

EASYPAYSA_NAME = "Jaffar Ali"
EASYPAYSA_NUMBER = "03486623402"

MEMBERSHIP_FEE = "$5 USD (Lifetime)"

# =============================================

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

# ============= STATES =============

SELECT_TYPE, GET_NAME, GET_EMAIL, GET_PROOF, GET_WHATSAPP, ADMIN_REVIEW, SELECT_PAYMENT, GET_PAYMENT_PROOF, FINAL_APPROVAL = range(9)

# ============= START COMMAND =============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle start command with all resume scenarios"""
    user = update.effective_user
    user_id = user.id
    username = user.username or "No username"
    first_name = user.first_name
    
    # Get existing user data
    user_data = get_user_data(user_id)
    
    if not user_data:
        # New user
        create_user(user_id, username)
        await send_welcome(update, first_name)
        return SELECT_TYPE
    
    # Existing user - check all possible states
    step = user_data[7]  # current_step
    status = user_data[11]  # status
    admin_approved = user_data[12]  # admin_approved
    
    # Case 1: Already fully approved and completed
    if status == 'completed':
        await update.message.reply_text(
            f"✅ *Welcome back {first_name}!*\n\n"
            f"You are already approved and have access to premium groups.\n\n"
            f"🔗 *Telegram Group:*\n{TELEGRAM_GROUP_LINK}\n\n"
            f"📱 *WhatsApp Group:*\n{WHATSAPP_GROUP_LINK}",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    # Case 2: Admin approved but payment pending (REMINDER MODE)
    if admin_approved == 1 and status == 'payment_pending':
        keyboard = [
            [InlineKeyboardButton("💰 Binance", callback_data='pay_binance')],
            [InlineKeyboardButton("📱 Easypaisa", callback_data='pay_easypaisa')]
        ]
        
        await update.message.reply_text(
            f"⏰ *Payment Reminder for {first_name}*\n\n"
            f"✅ Your submitted information has been *reviewed and approved* by admin!\n\n"
            f"💳 *Only payment is remaining to join Premium Group.*\n\n"
            f"💎 *Membership Fee:* {MEMBERSHIP_FEE}\n\n"
            f"⚠️ *Please complete your payment now to get instant access.*\n\n"
            f"👇 *Select payment method:*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        return SELECT_PAYMENT
    
    # Case 3: Info submitted, waiting for admin review
    if step == 'info_submitted' and admin_approved == 0:
        await update.message.reply_text(
            f"⏳ *Hello {first_name}!*\n\n"
            f"✅ Your information has already been submitted for admin review.\n\n"
            f"🕐 *Status: PENDING*\n"
            f"Please wait... Admin will review and respond soon.\n\n"
            f"🔔 You will receive a notification once approved.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    # Case 4: Payment proof submitted, waiting for verification
    if step == 'payment_submitted':
        await update.message.reply_text(
            f"⏳ *Hello {first_name}!*\n\n"
            f"✅ Your payment proof has been submitted.\n\n"
            f"🕐 *Status: UNDER VERIFICATION*\n"
            f"Admin is verifying your payment...\n\n"
            f"🔔 You will receive group links once verified.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    # Case 5: Resume from where left
    if step == 'name_pending':
        await update.message.reply_text(
            f"🔄 *Welcome back {first_name}!*\n\n"
            f"Please complete your previous application.\n\n"
            f"📝 *Step 1/4: Enter your full name:*",
            parse_mode=ParseMode.MARKDOWN
        )
        return GET_NAME
    
    if step == 'email_pending':
        await update.message.reply_text(
            f"🔄 *Welcome back {first_name}!*\n\n"
            f"✅ Name: *{user_data[2]}*\n\n"
            f"📧 *Step 2/4: Enter your email address:*",
            parse_mode=ParseMode.MARKDOWN
        )
        return GET_EMAIL
    
    if step == 'proof_pending':
        request_type = user_data[5] or "purchase"
        await update.message.reply_text(
            f"🔄 *Welcome back {first_name}!*\n\n"
            f"📸 *You haven't submitted your {request_type} proof yet.*\n\n"
            f"Please send the screenshot/image:",
            parse_mode=ParseMode.MARKDOWN
        )
        return GET_PROOF
    
    if step == 'whatsapp_pending':
        await update.message.reply_text(
            f"🔄 *Welcome back {first_name}!*\n\n"
            f"✅ Name: *{user_data[2]}*\n"
            f"✅ Email: *{user_data[3]}*\n"
            f"✅ Proof received\n\n"
            f"📱 *Step 4/4: Enter your WhatsApp number (with country code):*\n\n"
            f"Example: +923001234567, +14155552671, +447911123456",
            parse_mode=ParseMode.MARKDOWN
        )
        return GET_WHATSAPP
    
    # Default - restart fresh
    await send_welcome(update, first_name)
    return SELECT_TYPE

async def send_welcome(update, first_name):
    """Send welcome message"""
    keyboard = [
        [InlineKeyboardButton("💎 Premium Subscription", callback_data='type_premium')],
        [InlineKeyboardButton("🛒 Product Purchase", callback_data='type_product')]
    ]
    
    await update.message.reply_text(
        f"👋 *Welcome {first_name}!*\n\n"
        f"What did you buy from my website?\n\n"
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
        f"💎 *To add you to the premium group, we need some information.*\n\n"
        f"📝 *Step 1/4: Enter your full name:*",
        parse_mode=ParseMode.MARKDOWN
    )
    return GET_NAME

# ============= COLLECT INFO =============

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get full name"""
    user_id = update.effective_user.id
    name = update.message.text
    
    if len(name) < 2:
        await update.message.reply_text(
            "❌ *Name too short!* Please enter your full name:",
            parse_mode=ParseMode.MARKDOWN
        )
        return GET_NAME
    
    update_user(user_id, 'full_name', name)
    update_step(user_id, 'email_pending')
    
    await update.message.reply_text(
        f"✅ *Name: {name}*\n\n"
        f"📧 *Step 2/4: Enter your email address:*",
        parse_mode=ParseMode.MARKDOWN
    )
    return GET_EMAIL

async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get email"""
    user_id = update.effective_user.id
    email = update.message.text.lower().strip()
    
    # Email validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        await update.message.reply_text(
            "❌ *Invalid email format!* Please enter a valid email:\n\n"
            f"Example: yourname@gmail.com",
            parse_mode=ParseMode.MARKDOWN
        )
        return GET_EMAIL
    
    update_user(user_id, 'email', email)
    update_step(user_id, 'proof_pending')
    
    # Get request type for message
    user_data = get_user_data(user_id)
    request_type = user_data[5] or "purchase"
    
    proof_text = "subscription proof" if request_type == "Premium Subscription" else "product proof"
    
    await update.message.reply_text(
        f"✅ *Email: {email}*\n\n"
        f"📸 *Step 3/4: Send your {proof_text} (screenshot/image):*\n\n"
        f"⚠️ *Please send a clear image showing:*\n"
        f"• Purchase/subscription details\n"
        f"• Payment confirmation\n"
        f"• Date and time visible",
        parse_mode=ParseMode.MARKDOWN
    )
    return GET_PROOF

async def get_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get proof screenshot"""
    user_id = update.effective_user.id
    
    if not update.message.photo:
        await update.message.reply_text(
            "❌ *Please send an image/screenshot!* Try again:",
            parse_mode=ParseMode.MARKDOWN
        )
        return GET_PROOF
    
    # Save photo
    photo = update.message.photo[-1]
    file_id = photo.file_id
    
    update_user(user_id, 'proof_file_id', file_id)
    update_step(user_id, 'whatsapp_pending')
    
    await update.message.reply_text(
        f"✅ *Proof received successfully!*\n\n"
        f"📱 *Step 4/4: Enter your WhatsApp number (with country code):*\n\n"
        f"Examples:\n"
        f"• Pakistan: +923001234567\n"
        f"• USA: +14155552671\n"
        f"• UK: +447911123456\n"
        f"• India: +919876543210",
        parse_mode=ParseMode.MARKDOWN
    )
    return GET_WHATSAPP

async def get_whatsapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get WhatsApp and submit to admin"""
    user_id = update.effective_user.id
    whatsapp = update.message.text.strip()
    
    # International phone validation
    # Remove spaces, dashes, and parentheses
    clean_number = re.sub(r'[\s\-\(\)\.]', '', whatsapp)
    
    # Check if starts with + and has 10-15 digits
    if not re.match(r'^\+\d{10,15}$', clean_number):
        await update.message.reply_text(
            "❌ *Invalid WhatsApp number!*\n\n"
            f"Please enter with country code:\n"
            f"• +923001234567 (Pakistan)\n"
            f"• +14155552671 (USA)\n"
            f"• +447911123456 (UK)\n"
            f"• +919876543210 (India)",
            parse_mode=ParseMode.MARKDOWN
        )
        return GET_WHATSAPP
    
    update_user(user_id, 'whatsapp', clean_number)
    update_step(user_id, 'info_submitted')
    
    # Confirm to user
    await update.message.reply_text(
        "✅ *Your information has been successfully submitted!*\n\n"
        "🕐 *It has been sent to admin for review.*\n\n"
        "⏳ Please wait...\n"
        "🔔 You will receive a notification once admin reviews your application.",
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
🆕 *NEW APPLICATION FOR REVIEW*

👤 *User:* @{user_data[1]}
🆔 *ID:* `{user_id}`
📋 *Type:* {user_data[5]}
📝 *Name:* {user_data[2]}
📧 *Email:* {user_data[3]}
📱 *WhatsApp:* {clean_number}
⏰ *Submitted:* {datetime.now().strftime('%Y-%m-%d %H:%M')}

👇 *Please review and take action:*
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
    
    # Update status - mark admin approved but payment pending
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET admin_approved = 1, status = 'payment_pending', current_step = 'payment_pending', updated_at = ? WHERE user_id = ?",
              (datetime.now(), user_id))
    conn.commit()
    conn.close()
    
    # Send fee message to user
    keyboard = [
        [InlineKeyboardButton("💰 Binance", callback_data='pay_binance')],
        [InlineKeyboardButton("📱 Easypaisa", callback_data='pay_easypaisa')]
    ]
    
    await context.bot.send_message(
        chat_id=user_id,
        text=f"""
🎉 *CONGRATULATIONS! YOUR APPLICATION IS APPROVED!*

✅ Admin has reviewed and *approved* your application!

💎 *To join Premium Group, please pay the Lifetime Membership Fee:*
💵 *{MEMBERSHIP_FEE}*

👇 *Select your payment method:*
        """,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    
    await query.edit_message_text(
        f"✅ *Approved!*\n\nUser `{user_id}` has been notified to complete payment.",
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
        f"*Please enter rejection reason:*",
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

You can apply again by sending /start
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

✅ *After payment, please send the screenshot here.*
        """
    else:
        details = f"""
📱 *EASYPAYSA PAYMENT DETAILS*

👤 *Account Name:* {EASYPAYSA_NAME}
📞 *Account Number:* `{EASYPAYSA_NUMBER}`

💵 *Amount:* {MEMBERSHIP_FEE}

✅ *After payment, please send the screenshot here.*
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
    
    if not user_data:
        return
    
    status = user_data[11]
    admin_approved = user_data[12]
    
    # Only process if admin approved and payment pending
    if not (admin_approved == 1 and status == 'payment_pending'):
        return
    
    if not update.message.photo:
        await update.message.reply_text(
            "❌ *Please send payment screenshot as image!*",
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
    c.execute("UPDATE users SET payment_file_id = ?, payment_hash = ?, current_step = ?, status = ? WHERE user_id = ?",
              (photo.file_id, image_hash, 'payment_submitted', 'payment_verification', user_id))
    conn.commit()
    conn.close()
    
    # Confirm to user
    await update.message.reply_text(
        "⏳ *Payment Screenshot Received!*\n\n"
        "✅ Admin is verifying your payment...\n"
        "🕐 *You will receive group links once verified.*\n\n"
        "⚠️ *Fake screenshots will result in permanent ban!*",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Send to admin
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve & Send Links", callback_data=f'finallink_{user_id}'),
            InlineKeyboardButton("❌ Reject Payment", callback_data=f'rejectpay_{user_id}')
        ]
    ]
    
    caption = f"""
💰 *NEW PAYMENT RECEIVED FOR VERIFICATION*

👤 *User:* @{user_data[1]}
🆔 *ID:* `{user_id}`
📝 *Name:* {user_data[2]}
📧 *Email:* {user_data[3]}
📱 *WhatsApp:* {user_data[4]}
💳 *Payment Method:* {user_data[8] or 'Not specified'}
⏰ *Received:* {datetime.now().strftime('%Y-%m-%d %H:%M')}

👇 *Please verify and take action:*
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
    
    # Update status to completed
    update_user(user_id, 'status', 'completed')
    update_step(user_id, 'completed')
    
    # Send links to user
    await context.bot.send_message(
        chat_id=user_id,
        text=f"""
🎉 *PAYMENT VERIFIED SUCCESSFULLY!*

✅ Your payment has been verified!

🔗 *TELEGRAM PREMIUM GROUP:*
{TELEGRAM_GROUP_LINK}

📱 *WHATSAPP PREMIUM GROUP:*
{WHATSAPP_GROUP_LINK}

⚠️ *Important Rules:*
• Do not share these links with anyone
• Follow all group rules
• Do not add fake members
• Lifetime access granted

🚀 *Welcome to Premium Family! Enjoy your access!*
        """,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=False
    )
    
    await query.edit_message_text(
        f"✅ *User {user_id} fully approved!*\nBoth group links sent.",
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
        f"❌ *Rejecting payment from user {user_id}*\n\n"
        f"*Please enter rejection reason:*",
        parse_mode=ParseMode.MARKDOWN
    )
    return FINAL_APPROVAL

# ============= CANCEL =============

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel"""
    await update.message.reply_text(
        "❌ Cancelled.\nSend /start to begin again."
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
    
    # Payment proof handler
    application.add_handler(MessageHandler(filters.PHOTO, receive_payment_proof))
    
    print("🤖 Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
