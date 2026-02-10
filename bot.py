import logging
import sqlite3
import hashlib
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ConversationHandler, ContextTypes, filters
from telegram.constants import ParseMode

# ============= APNI DETAILS YAHAN DAALEN =============

BOT_TOKEN = "8535390425:AAFLbRWHfy9reLO94h91N5wlAou4gxfgK3c"
ADMIN_ID = 7291034213  # YAHAN_APNA_TELEGRAM_ID_DAALEN

# GROUP LINKS
TELEGRAM_GROUP_LINK = "https://t.me/+P8gZuIBH75RiOThk"

# PAYMENT DETAILS
BINANCE_EMAIL = "techmasterfreelancer@gmail.com"
BINANCE_ID = "1129541950"
BINANCE_NETWORK = "TRC20"

EASYPAYSA_NAME = "Jaffar Ali"
EASYPAYSA_NUMBER = "03486623402"

MEMBERSHIP_FEE = "$5 USD (Lifetime)"

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
    
    # If already approved
    if status == 'approved':
        await update.message.reply_text(
            f"✅ *Welcome back {user.first_name}!*\n\n"
            f"Aap already approved hain.\n\n"
            f"🔗 *Telegram Group:*\n{TELEGRAM_GROUP_LINK}\n\n"
            f"📱 *WhatsApp Group:*\n{WHATSAPP_GROUP_LINK}",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    # If payment pending
    if status == 'payment_pending':
        keyboard = [
            [InlineKeyboardButton("💰 Binance", callback_data='pay_binance')],
            [InlineKeyboardButton("📱 Easypaisa", callback_data='pay_easypaisa')]
        ]
        await update.message.reply_text(
            f"👋 *Welcome back {user.first_name}!*\n\n"
            f"💎 *Premium Group Join Karne Ke Liye:*\n"
            f"💵 *Fee:* {MEMBERSHIP_FEE}\n\n"
            f"👇 *Payment method select karein:*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        return SELECT_PAYMENT
    
    # If proof submitted, waiting for admin
    if step == 'proof_submitted':
        await update.message.reply_text(
            f"⏳ *Welcome back {user.first_name}!*\n\n"
            f"Aapki application admin ke paas hai.\n"
            f"🕐 *Approval ka intezaar karein...*\n\n"
            f"Jab admin approve karega, aapko fee payment ka message mil jayega.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    # If payment proof submitted
    if step == 'payment_submitted':
        await update.message.reply_text(
            f"⏳ *Welcome back {user.first_name}!*\n\n"
            f"Aapka payment proof admin ke paas hai.\n"
            f"🕐 *Verification ka intezaar karein...*",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    # Resume from where left
    if step == 'name_pending':
        await update.message.reply_text(
            f"🔄 *Welcome back {user.first_name}!*\n\n"
            f"📝 *Apna full name bataiye:*",
            parse_mode=ParseMode.MARKDOWN
        )
        return GET_NAME
    
    if step == 'email_pending':
        await update.message.reply_text(
            f"🔄 *Welcome back {user.first_name}!*\n\n"
            f"✅ Name: *{user_data[2]}*\n\n"
            f"📧 *Apna email bataiye:*",
            parse_mode=ParseMode.MARKDOWN
        )
        return GET_EMAIL
    
    if step == 'proof_pending':
        request_type = user_data[5] or "product"
        await update.message.reply_text(
            f"🔄 *Welcome back {user.first_name}!*\n\n"
            f"📸 *Aapne {request_type} ka proof nahi bheja.*\n\n"
            f"Please screenshot bhejein:",
            parse_mode=ParseMode.MARKDOWN
        )
        return GET_PROOF
    
    if step == 'whatsapp_pending':
        await update.message.reply_text(
            f"🔄 *Welcome back {user.first_name}!*\n\n"
            f"✅ Name: *{user_data[2]}*\n"
            f"✅ Email: *{user_data[3]}*\n"
            f"✅ Proof received\n\n"
            f"📱 *Apna WhatsApp number bataiye:*",
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
        f"Kya aapne meri website se *Premium Subscription* buy ki hai ya *koi Product* buy kiya hai?\n\n"
        f"👇 *Select karein:*",
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
        f"💎 *Premium group mein add hone ke liye kuch information li jayegi.*\n\n"
        f"📝 *Step 1/4: Apna full name bataiye:*",
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
        f"📧 *Step 2/4: Apna email address bataiye:*",
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
            "❌ *Invalid email!* Sahi email bataiye:",
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
        f"📸 *Step 3/4: Apne {request_type} ka proof/screenshot bhejiye:*\n\n"
        f"⚠️ *Clear image honi chahiye jisme details dikhein*",
        parse_mode=ParseMode.MARKDOWN
    )
    return GET_PROOF

async def get_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get proof screenshot"""
    user_id = update.effective_user.id
    
    if not update.message.photo:
        await update.message.reply_text(
            "❌ *Please image bhejiye!* Screenshot bhejein:",
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
        f"📱 *Step 4/4: Apna WhatsApp number bataiye (country code ke saath):*\n\n"
        f"Example: +923001234567",
        parse_mode=ParseMode.MARKDOWN
    )
    return GET_WHATSAPP

async def get_whatsapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get WhatsApp and submit to admin"""
    user_id = update.effective_user.id
    whatsapp = update.message.text
    
    # Basic validation
    if len(whatsapp) < 10 or not whatsapp.replace('+', '').replace('-', '').isdigit():
        await update.message.reply_text(
            "❌ *Invalid number!* Sahi WhatsApp number bataiye:\n\n"
            f"Example: +923001234567",
            parse_mode=ParseMode.MARKDOWN
        )
        return GET_WHATSAPP
    
    update_user(user_id, 'whatsapp', whatsapp)
    update_step(user_id, 'proof_submitted')
    
    # Confirm to user
    await update.message.reply_text(
        "✅ *Aapki information successfully submit ho gayi hai!*\n\n"
        "🕐 *Aap se jald contact kiya jayega.*\n\n"
        "⏳ Admin review kar raha hai...\n"
        "🔔 Jab approve hoga, aapko fee payment ka message mil jayega.",
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
📱 *WhatsApp:* {whatsapp}
⏰ *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M')}

👇 *Action karein:*
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
    
    # Update status
    update_user(user_id, 'status', 'payment_pending')
    update_step(user_id, 'payment_pending')
    
    # Send fee message to user
    keyboard = [
        [InlineKeyboardButton("💰 Binance", callback_data='pay_binance')],
        [InlineKeyboardButton("📱 Easypaisa", callback_data='pay_easypaisa')]
    ]
    
    await context.bot.send_message(
        chat_id=user_id,
        text=f"""
🎉 *APPLICATION APPROVED!*

✅ Admin ne aapki application *verify* kar li hai!

💎 *Premium Group Join Karne Ke Liye Lifetime Fee:*
💵 *{MEMBERSHIP_FEE}*

👇 *Payment method select karein:*
        """,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    
    await query.edit_message_text(
        f"✅ *Approved!*\n\nUser `{user_id}` ko fee message bhej diya.",
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
        f"*Reason bataiye (message bhejein):*",
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

Aapki application reject kar di gayi hai.

*Reason:* {reason}

Dubara apply karne ke liye /start karein.
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

✅ *Payment karne ke baad screenshot yahan bhejein.*
        """
    else:
        details = f"""
📱 *EASYPAYSA PAYMENT DETAILS*

👤 *Name:* {EASYPAYSA_NAME}
📞 *Number:* `{EASYPAYSA_NUMBER}`

💵 *Amount:* {MEMBERSHIP_FEE}

✅ *Payment karne ke baad screenshot yahan bhejein.*
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
            "❌ *Please payment ka screenshot bhejiye!*",
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
            "🚫 *YE SCREENSHOT PEHLE USE HO CHUKA HAI!*",
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
        "✅ Admin verify kar raha hai...\n"
        "🕐 *Approval ke baad aapko group link mil jayega.*\n\n"
        "⚠️ *Fake screenshot par ban lag sakta hai!*",
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

👇 *Verify karein:*
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

✅ Aapki payment verify ho gayi hai!

🔗 *TELEGRAM GROUP:*
{TELEGRAM_GROUP_LINK}

📱 *WHATSAPP GROUP:*
{WHATSAPP_GROUP_LINK}

⚠️ *Important:*
• Links share nahi karein
• Group rules follow karein
• Fake members add nahi karein

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
        f"*Reason bataiye:*",
        parse_mode=ParseMode.MARKDOWN
    )
    return FINAL_APPROVAL

# ============= CANCEL =============

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel"""
    await update.message.reply_text(
        "❌ Cancelled.\nDubara shuru karne ke liye /start karein."
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
    
    print("🤖 Bot chal raha hai...")
    application.run_polling()

if __name__ == "__main__":
    main()
