import logging
import sqlite3
import hashlib
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ConversationHandler, ContextTypes, filters
from telegram.constants import ParseMode

# ============= APNI DETAILS YAHAN DAALEN =============

BOT_TOKEN = "8535390425:AAH4RF9v6k8H6fMQeXr_OQ6JuB7PV8gvgLs"
ADMIN_ID = 7291034213  # YAHAN_APNA_TELEGRAM_ID_DAALEN

# GROUP/CHANNEL LINKS
WHATSAPP_GROUP_LINK = "https://chat.whatsapp.com/YAHAN_WHATSAPP_LINK_DAALEN"

# PAYMENT DETAILS
BINANCE_EMAIL = "aapka.binance@email.com"
BINANCE_ID = "123456789"
BINANCE_NETWORK = "TRC20"  # Ya jo bhi network use karte hain

EASYPAYSA_NAME = "Aapka Naam"
EASYPAYSA_NUMBER = "03XX-XXXXXXX"

# FEE AMOUNT
MEMBERSHIP_FEE = "$5 USD"

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
        product_ss TEXT,
        status TEXT DEFAULT 'info_collected',
        payment_status TEXT DEFAULT 'pending',
        payment_method TEXT,
        payment_hash TEXT UNIQUE,
        payment_ss TEXT,
        info_step INTEGER DEFAULT 0,
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

def get_user_status(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result

def save_user_progress(user_id, username, field, value, step):
    conn = get_db()
    c = conn.cursor()
    
    # Check if user exists
    c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    exists = c.fetchone()
    
    if exists:
        # Update existing
        c.execute(f"UPDATE users SET {field} = ?, info_step = ?, updated_at = ? WHERE user_id = ?",
                  (value, step, datetime.now(), user_id))
    else:
        # Insert new
        c.execute('''INSERT INTO users 
                     (user_id, username, info_step, created_at, updated_at) 
                     VALUES (?, ?, ?, ?, ?)''',
                  (user_id, username, step, datetime.now(), datetime.now()))
        # Now update the specific field
        c.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))
    
    conn.commit()
    conn.close()

def update_user_step(user_id, step):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET info_step = ?, updated_at = ? WHERE user_id = ?",
              (step, datetime.now(), user_id))
    conn.commit()
    conn.close()

def save_product_ss(user_id, file_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET product_ss = ?, status = ?, updated_at = ? WHERE user_id = ?",
              (file_id, 'awaiting_approval', datetime.now(), user_id))
    conn.commit()
    conn.close()

def update_to_payment_phase(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET status = ?, updated_at = ? WHERE user_id = ?",
              ('payment_pending', datetime.now(), user_id))
    conn.commit()
    conn.close()

def save_payment_method(user_id, method):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET payment_method = ?, updated_at = ? WHERE user_id = ?",
              (method, datetime.now(), user_id))
    conn.commit()
    conn.close()

def save_payment_ss(user_id, hash_val, file_id):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("UPDATE users SET payment_hash = ?, payment_ss = ?, payment_status = ?, updated_at = ? WHERE user_id = ?",
                  (hash_val, file_id, 'awaiting_approval', datetime.now(), user_id))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def check_duplicate_screenshot(file_hash):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT user_id FROM screenshots WHERE file_hash = ?", (file_hash,))
    result = c.fetchone()
    conn.close()
    return result

def save_screenshot_hash(file_hash, user_id):
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

def approve_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET payment_status = ?, updated_at = ? WHERE user_id = ?",
              ('approved', datetime.now(), user_id))
    conn.commit()
    conn.close()

# ============= CONVERSATION STATES =============

(
    SELECT_TYPE,      # 0 - User selects Premium or Product
    GET_NAME,         # 1 - Get full name
    GET_EMAIL,        # 2 - Get email
    GET_WHATSAPP,     # 3 - Get WhatsApp number
    GET_PRODUCT_SS,   # 4 - Get product screenshot
    AWAITING_ADMIN,   # 5 - Waiting for admin
    SELECT_PAYMENT,   # 6 - Select Binance or Easypaisa
    GET_PAYMENT_SS,   # 7 - Get payment screenshot
    AWAITING_PAYMENT_APPROVAL  # 8 - Waiting for payment approval
) = range(9)

# ============= START COMMAND =============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - check user status and resume if needed"""
    user = update.effective_user
    user_id = user.id
    
    # Check if user exists and their status
    user_data = get_user_status(user_id)
    
    if user_data:
        status = user_data[4]  # status column
        step = user_data[11]   # info_step column
        request_type = user_data[5]  # request_type
        
        # If already approved
        if user_data[7] == 'approved':  # payment_status
            await update.message.reply_text(
                f"✅ *Aap already approved hain!*\n\n"
                f"🔗 *Premium Group Link:*\n{PREMIUM_GROUP_LINK}\n\n"
                f"📱 *WhatsApp Group:*\n{WHATSAPP_GROUP_LINK}",
                parse_mode=ParseMode.MARKDOWN
            )
            return ConversationHandler.END
        
        # If awaiting payment (admin sent fee message)
        if status == 'payment_pending':
            keyboard = [
                [InlineKeyboardButton("💰 Binance", callback_data='payment_binance')],
                [InlineKeyboardButton("📱 Easypaisa", callback_data='payment_easypaisa')]
            ]
            await update.message.reply_text(
                "💎 *Premium Group Join Karne Ke Liye:*\n\n"
                f"💵 *Fee:* {MEMBERSHIP_FEE}\n\n"
                "👇 *Payment method select karein:*",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return SELECT_PAYMENT
        
        # If info was being collected, resume from where left
        if step == 1 and not user_data[2]:  # Has no name
            await update.message.reply_text(
                "🔄 *Welcome Back!*\n\n"
                "📝 *Step 1/3: Apna full name bataiye:*",
                parse_mode=ParseMode.MARKDOWN
            )
            return GET_NAME
        
        if step == 2 and not user_data[3]:  # Has no email
            await update.message.reply_text(
                "🔄 *Welcome Back!*\n\n"
                f"✅ Name: *{user_data[2]}*\n\n"
                "📧 *Step 2/3: Apna email bataiye:*",
                parse_mode=ParseMode.MARKDOWN
            )
            return GET_EMAIL
        
        if step == 3 and not user_data[4]:  # Has no whatsapp
            await update.message.reply_text(
                "🔄 *Welcome Back!*\n\n"
                f"✅ Name: *{user_data[2]}*\n"
                f"✅ Email: *{user_data[3]}*\n\n"
                "📱 *Step 3/3: Apna WhatsApp number bataiye:*",
                parse_mode=ParseMode.MARKDOWN
            )
            return GET_WHATSAPP
        
        if step == 4 and not user_data[6]:  # Has no product screenshot
            await update.message.reply_text(
                "🔄 *Welcome Back!*\n\n"
                f"📸 *Aapne {request_type} ka screenshot nahi bheja.*\n\n"
                "Please screenshot bhejein:",
                parse_mode=ParseMode.MARKDOWN
            )
            return GET_PRODUCT_SS
    
    # New user - welcome message
    keyboard = [
        [InlineKeyboardButton("💎 Premium Subscription", callback_data='type_premium')],
        [InlineKeyboardButton("🛒 Product Purchase", callback_data='type_product')]
    ]
    
    await update.message.reply_text(
        "👋 *Welcome to Premium Support!*\n\n"
        "Kya aap hamari *Premium Subscription* lena chahte hain ya *Product* buy karna chahte hain?\n\n"
        "👇 *Select karein:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    return SELECT_TYPE

# ============= TYPE SELECTION =============

async def select_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Premium or Product selection"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    username = update.effective_user.username or "No username"
    
    data = query.data.split('_')
    request_type = "Premium Subscription" if data[1] == 'premium' else "Product Purchase"
    
    # Save to database
    save_user_progress(user_id, username, 'request_type', request_type, 1)
    
    await query.edit_message_text(
        f"✅ *{request_type}* selected!\n\n"
        "📝 *Step 1/3: Apna full name bataiye:*",
        parse_mode=ParseMode.MARKDOWN
    )
    return GET_NAME

# ============= COLLECT USER INFO =============

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get user's full name"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "No username"
    name = update.message.text
    
    save_user_progress(user_id, username, 'full_name', name, 2)
    
    await update.message.reply_text(
        f"✅ Name: *{name}*\n\n"
        "📧 *Step 2/3: Apna email address bataiye:*",
        parse_mode=ParseMode.MARKDOWN
    )
    return GET_EMAIL

async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get user's email"""
    user_id = update.effective_user.id
    email = update.message.text
    
    # Validate email
    if "@" not in email or "." not in email:
        await update.message.reply_text(
            "❌ *Invalid email!* Sahi email address bataiye:",
            parse_mode=ParseMode.MARKDOWN
        )
        return GET_EMAIL
    
    save_user_progress(user_id, None, 'email', email, 3)
    
    await update.message.reply_text(
        f"✅ Email: *{email}*\n\n"
        "📱 *Step 3/3: Apna WhatsApp number bataiye (with country code):*",
        parse_mode=ParseMode.MARKDOWN
    )
    return GET_WHATSAPP

async def get_whatsapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get WhatsApp number and ask for screenshot"""
    user_id = update.effective_user.id
    whatsapp = update.message.text
    
    # Basic validation
    if len(whatsapp) < 10:
        await update.message.reply_text(
            "❌ *Invalid number!* Sahi WhatsApp number bataiye:",
            parse_mode=ParseMode.MARKDOWN
        )
        return GET_WHATSAPP
    
    save_user_progress(user_id, None, 'whatsapp', whatsapp, 4)
    
    # Get user data to show what they selected
    user_data = get_user_status(user_id)
    request_type = user_data[5] if user_data else "product"
    
    await update.message.reply_text(
        f"✅ WhatsApp: *{whatsapp}*\n\n"
        f"📸 *Ab apne {request_type} ka screenshot bhejiye:*\n\n"
        "⚠️ *Clear screenshot hona chahiye jismein:*\n"
        "• Product/Subscription details dikhein\n"
        "• Payment confirmation ho\n"
        "• Date/Time dikhe",
        parse_mode=ParseMode.MARKDOWN
    )
    return GET_PRODUCT_SS

async def get_product_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get product/subscription screenshot"""
    user_id = update.effective_user.id
    
    if not update.message.photo:
        await update.message.reply_text(
            "❌ *Please send a valid image/screenshot!*",
            parse_mode=ParseMode.MARKDOWN
        )
        return GET_PRODUCT_SS
    
    # Get largest photo
    photo = update.message.photo[-1]
    file_id = photo.file_id
    
    # Save to database
    save_product_ss(user_id, file_id)
    
    # Get user data for admin message
    user_data = get_user_status(user_id)
    
    # Confirm to user
    await update.message.reply_text(
        "⏳ *Information Submitted!*\n\n"
        "✅ Aapki details admin ke paas bhej di gayi hain.\n"
        "🕐 *Approval ka intezaar karein...*\n\n"
        "🔔 Jab admin approve karega, aapko fee payment ka message mil jayega.\n\n"
        "⚠️ *Note:* Fake screenshots par permanent ban ho sakta hai!",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Send to admin
    keyboard = [
        [
            InlineKeyboardButton("✅ Send Fee Message", callback_data=f'fee_{user_id}'),
            InlineKeyboardButton("❌ Reject", callback_data=f'rejectinfo_{user_id}')
        ]
    ]
    
    caption = f"""
🆕 *NEW APPLICATION*

👤 *User:* @{user_data[1]}
🆔 *ID:* `{user_id}`
📋 *Type:* {user_data[5]}
📝 *Name:* {user_data[2]}
📧 *Email:* {user_data[3]}
📱 *WhatsApp:* {user_data[4]}
⏰ *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M')}

👇 *Action karein:*
    """
    
    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=file_id,
        caption=caption,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ConversationHandler.END

# ============= ADMIN ACTIONS =============

async def admin_send_fee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin sends fee message to user"""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split('_')[1])
    
    # Update user status
    update_to_payment_phase(user_id)
    
    # Send fee message to user
    keyboard = [
        [InlineKeyboardButton("💰 Binance", callback_data='payment_binance')],
        [InlineKeyboardButton("📱 Easypaisa", callback_data='payment_easypaisa')]
    ]
    
    fee_message = f"""
🎉 *APPLICATION APPROVED!*

✅ Admin ne aapki application *verify* kar li hai!

💎 *Premium Group Join Karne Ke Liye Fee:*
💵 *{MEMBERSHIP_FEE}*

👇 *Payment method select karein:*
    """
    
    await context.bot.send_message(
        chat_id=user_id,
        text=fee_message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    
    await query.edit_message_text(
        f"✅ *Fee message sent to user {user_id}*",
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_reject_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin rejects initial application"""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split('_')[1])
    context.user_data['reject_user_id'] = user_id
    context.user_data['reject_stage'] = 'info'
    
    await query.edit_message_text(
        f"❌ *Rejecting user {user_id}*\n\n"
        f"Rejection reason bataiye:",
        parse_mode=ParseMode.MARKDOWN
    )
    return AWAITING_ADMIN

async def handle_rejection_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle rejection reason from admin"""
    reason = update.message.text
    user_id = context.user_data.get('reject_user_id')
    
    if not user_id:
        await update.message.reply_text("Error!")
        return ConversationHandler.END
    
    # Send to user
    reject_msg = f"""
❌ *APPLICATION REJECTED*

Aapki application reject kar di gayi hai.

*Reason:* {reason}

Agar aapko lagta hai ye mistake hai, toh dubara /start karke apply karein.
    """
    
    await context.bot.send_message(chat_id=user_id, text=reject_msg, parse_mode=ParseMode.MARKDOWN)
    await update.message.reply_text(f"❌ User {user_id} rejected.")
    
    return ConversationHandler.END

# ============= PAYMENT FLOW =============

async def show_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Binance or Easypaisa details"""
    query = update.callback_query
    await query.answer()
    
    method = query.data.split('_')[1]
    user_id = update.effective_user.id
    
    # Save payment method
    save_payment_method(user_id, method.capitalize())
    
    if method == 'binance':
        details = f"""
💰 *BINANCE PAYMENT DETAILS*

📧 *Email:* `{BINANCE_EMAIL}`
🆔 *Binance ID:* `{BINANCE_ID}`
🌐 *Network:* `{BINANCE_NETWORK}`

💵 *Amount:* {MEMBERSHIP_FEE}

✅ *Payment karne ke baad screenshot yahan bhejein.*
        """
    else:  # easypaisa
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
    
    # Store that we're waiting for payment screenshot
    context.user_data['awaiting_payment_ss'] = user_id

async def receive_payment_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive payment screenshot"""
    user_id = update.effective_user.id
    
    # Check if user is in payment phase
    user_data = get_user_status(user_id)
    
    if not user_data or user_data[4] != 'payment_pending':  # status
        # Maybe it's a product screenshot for new user
        # Let the conversation handler deal with it
        return
    
    if not update.message.photo:
        await update.message.reply_text("❌ Please send payment screenshot as image!")
        return
    
    # Process screenshot
    photo = update.message.photo[-1]
    photo_file = await photo.get_file()
    
    # Check duplicate
    file_bytes = await photo_file.download_as_bytearray()
    image_hash = hashlib.md5(file_bytes).hexdigest()
    
    duplicate = check_duplicate_screenshot(image_hash)
    if duplicate:
        await update.message.reply_text(
            "🚫 *YE SCREENSHOT PEHLE USE HO CHUKA HAI!*",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Save
    save_screenshot_hash(image_hash, user_id)
    
    if not save_payment_ss(user_id, image_hash, photo.file_id):
        await update.message.reply_text("❌ Error! Dobara try karein.")
        return
    
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
            InlineKeyboardButton("✅ Approve & Send Link", callback_data=f'approvelink_{user_id}'),
            InlineKeyboardButton("❌ Reject Payment", callback_data=f'rejectpay_{user_id}')
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

async def admin_approve_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin approves and sends group link"""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split('_')[1])
    
    # Approve
    approve_user(user_id)
    
    # Send to user
    success_msg = f"""
🎉 *PAYMENT APPROVED!*

✅ Aapki payment verify ho gayi hai!

🔗 *TELEGRAM PREMIUM GROUP:*
{PREMIUM_GROUP_LINK}

📱 *WHATSAPP GROUP:*
{WHATSAPP_GROUP_LINK}

⚠️ *Important:*
• Links share nahi karein
• Group rules follow karein
• Fake members add nahi karein

🚀 *Welcome to Premium Family!*
    """
    
    await context.bot.send_message(
        chat_id=user_id,
        text=success_msg,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=False
    )
    
    await query.edit_message_text(
        f"✅ *User {user_id} approved!*\nGroup links sent.",
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_reject_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin rejects payment"""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split('_')[1])
    context.user_data['reject_user_id'] = user_id
    context.user_data['reject_stage'] = 'payment'
    
    await query.edit_message_text(
        f"❌ *Rejecting payment {user_id}*\n\n"
        f"Rejection reason bataiye:",
        parse_mode=ParseMode.MARKDOWN
    )
    return AWAITING_ADMIN

# ============= CANCEL =============

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel conversation"""
    await update.message.reply_text(
        "❌ Process cancelled.\nDubara shuru karne ke liye /start karein."
    )
    return ConversationHandler.END

# ============= MAIN =============

def main():
    """Start the bot"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Main conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECT_TYPE: [CallbackQueryHandler(select_type, pattern='^type_')],
            GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            GET_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
            GET_WHATSAPP: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_whatsapp)],
            GET_PRODUCT_SS: [MessageHandler(filters.PHOTO, get_product_screenshot)],
            AWAITING_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_rejection_reason)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(conv_handler)
    
    # Admin callbacks
    application.add_handler(CallbackQueryHandler(admin_send_fee, pattern='^fee_'))
    application.add_handler(CallbackQueryHandler(admin_reject_info, pattern='^rejectinfo_'))
    application.add_handler(CallbackQueryHandler(show_payment_details, pattern='^payment_'))
    application.add_handler(CallbackQueryHandler(admin_approve_link, pattern='^approvelink_'))
    application.add_handler(CallbackQueryHandler(admin_reject_payment, pattern='^rejectpay_'))
    
    # Payment screenshot handler
    application.add_handler(MessageHandler(filters.PHOTO, receive_payment_screenshot))
    
    print("🤖 Bot chal raha hai...")
    application.run_polling()

if __name__ == "__main__":
    main()
