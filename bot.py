import logging
import sqlite3
import hashlib
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.constants import ParseMode

# ============= YOUR DETAILS =============
BOT_TOKEN = "8535390425:AAH4RF9v6k8H6fMQeXr_OQ6JuB7PV8gvgLs"
ADMIN_ID = 7291034213
TELEGRAM_GROUP_LINK = "https://t.me/+P8gZuIBH75RiOThk"
WHATSAPP_GROUP_LINK = "https://chat.whatsapp.com/YOUR_WHATSAPP_LINK"

BINANCE_EMAIL = "techmasterfreelancer@gmail.com"
BINANCE_ID = "1129541950"
BINANCE_NETWORK = "TRC20"

EASYPAYSA_NAME = "Jaffar Ali"
EASYPAYSA_NUMBER = "03486623402"
MEMBERSHIP_FEE = "$5 USD (Lifetime)"

# ========================================

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = 'bot.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, email TEXT,
        whatsapp TEXT, request_type TEXT, proof_file_id TEXT, current_step TEXT DEFAULT 'start',
        payment_method TEXT, payment_file_id TEXT, payment_hash TEXT UNIQUE,
        status TEXT DEFAULT 'new', admin_approved INTEGER DEFAULT 0,
        created_at TIMESTAMP, updated_at TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS screenshots (id INTEGER PRIMARY KEY, file_hash TEXT UNIQUE, user_id INTEGER, used_at TIMESTAMP)''')
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
    c.execute('INSERT OR IGNORE INTO users (user_id, username, current_step, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)',
              (user_id, username, 'start', 'new', datetime.now(), datetime.now()))
    conn.commit()
    conn.close()

def update_user(user_id, field, value):
    conn = get_db()
    c = conn.cursor()
    c.execute(f"UPDATE users SET {field} = ?, updated_at = ? WHERE user_id = ?", (value, datetime.now(), user_id))
    conn.commit()
    conn.close()

def save_hash(file_hash, user_id):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO screenshots (file_hash, user_id, used_at) VALUES (?, ?, ?)", (file_hash, user_id, datetime.now()))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

# ============= MESSAGES (FIXED - NO MARKDOWN ERRORS) =============

WELCOME_MESSAGE = """🎉 Welcome to Premium Support Bot!

Hello {name}! 👋

👇 Please select what you purchased from our website:"""

TYPE_SELECTED_MESSAGE = """✅ {type} selected!

📝 Step 1 of 4: Enter your FULL NAME

Example: Muhammad Ahmed Khan"""

EMAIL_MESSAGE = """✅ Thank you, {name}!

📧 Step 2 of 4: Enter your EMAIL

⚠️ IMPORTANT: Use the SAME email you used for website registration!

Example: yourname@gmail.com"""

PROOF_MESSAGE = """✅ Email saved!

📸 Step 3 of 4: Upload PROOF

For {type}:
• Screenshot of purchase, OR
• Payment receipt/invoice

✅ Clear image required
❌ Fake = Permanent ban"""

WHATSAPP_MESSAGE = """✅ Proof received!

📱 Step 4 of 4: WhatsApp Number

Enter with country code:
• Pakistan: +923001234567
• USA: +14155552671
• UK: +447911123456"""

SUBMITTED_MESSAGE = """🎊 Application Submitted!

✅ Your information has been sent to admin.

⏳ Status: PENDING REVIEW
🕐 Time: 2-24 hours

🔔 You'll be notified when approved!"""

# ============= ADMIN NOTIFICATION (PLAIN TEXT - NO ERRORS) =============

def get_admin_notification(user_id, username, request_type, full_name, email, whatsapp, time_now):
    """Plain text notification - no markdown errors"""
    return f"""🚨 NEW APPLICATION - ACTION REQUIRED

👤 APPLICANT DETAILS
━━━━━━━━━━━━━━━━━━━━━
🆔 User ID: {user_id}
👤 Username: @{username}
📌 Purchase Type: {request_type}

📝 PERSONAL INFORMATION
━━━━━━━━━━━━━━━━━━━━━
• Full Name: {full_name}
• Email: {email}
• WhatsApp: {whatsapp}

⏰ Submitted: {time_now}

📸 Proof of purchase attached above

👇 Click button below to approve or reject:"""

# ============= BOT FUNCTIONS =============

async def start(update: Update, context):
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name
    
    user_data = get_user(user_id)
    
    if not user_data:
        create_user(user_id, user.username or "No username")
        keyboard = [
            [InlineKeyboardButton("💎 Premium Subscription", callback_data='type_premium')],
            [InlineKeyboardButton("🛒 Product Purchase", callback_data='type_product')]
        ]
        await update.message.reply_text(
            WELCOME_MESSAGE.format(name=first_name),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    status = user_data[11]
    admin_approved = user_data[12]
    step = user_data[7]
    
    if status == 'completed':
        await update.message.reply_text(
            f"✅ Welcome back! You have access.\n\n"
            f"🔗 Telegram: {TELEGRAM_GROUP_LINK}"
        )
        return
    
    if admin_approved == 1 and status == 'payment_pending':
        keyboard = [
            [InlineKeyboardButton("💰 Pay with Binance", callback_data='pay_binance')],
            [InlineKeyboardButton("📱 Pay with Easypaisa", callback_data='pay_easypaisa')]
        ]
        await update.message.reply_text(
            f"✅ APPROVED! Pay {MEMBERSHIP_FEE}:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if step == 'info_submitted':
        await update.message.reply_text("⏳ Your application is pending review...")
        return
    
    if step == 'payment_submitted':
        await update.message.reply_text("⏳ Payment is being verified...")
        return
    
    # Resume
    if step == 'name_pending':
        await update.message.reply_text("📝 Enter your FULL NAME:")
    elif step == 'email_pending':
        await update.message.reply_text(f"📧 Enter EMAIL (same as website):")
    elif step == 'proof_pending':
        await update.message.reply_text(f"📸 Upload proof (screenshot or invoice):")
    elif step == 'whatsapp_pending':
        await update.message.reply_text(f"📱 Enter WhatsApp (+923001234567):")
    else:
        keyboard = [
            [InlineKeyboardButton("💎 Premium Subscription", callback_data='type_premium')],
            [InlineKeyboardButton("🛒 Product Purchase", callback_data='type_product')]
        ]
        await update.message.reply_text(
            WELCOME_MESSAGE.format(name=first_name),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    # Type selection
    if data.startswith('type_'):
        type_choice = data.split('_')[1]
        request_type = "Premium Subscription" if type_choice == 'premium' else "Product Purchase"
        
        update_user(user_id, 'request_type', request_type)
        update_user(user_id, 'current_step', 'name_pending')
        
        await query.edit_message_text(TYPE_SELECTED_MESSAGE.format(type=request_type))
        return
    
    # Payment selection
    if data.startswith('pay_'):
        method = data.split('_')[1]
        update_user(user_id, 'payment_method', method.capitalize())
        
        if method == 'binance':
            text = f"""💰 BINANCE PAYMENT

📧 Email: {BINANCE_EMAIL}
🆔 Binance ID: {BINANCE_ID}
💵 Amount: {MEMBERSHIP_FEE}

✅ Send screenshot after payment"""
        else:
            text = f"""📱 EASYPAYSA PAYMENT

👤 Name: {EASYPAYSA_NAME}
📞 Number: {EASYPAYSA_NUMBER}
💵 Amount: {MEMBERSHIP_FEE}

✅ Send screenshot after payment"""
        
        await query.edit_message_text(text)
        return
    
    # Admin approve - REMOVE BUTTONS AFTER CLICK
    if data.startswith('approve_'):
        try:
            target_id = int(data.split('_')[1])
            
            # Update database
            conn = get_db()
            c = conn.cursor()
            c.execute("UPDATE users SET admin_approved = 1, status = 'payment_pending', current_step = 'payment_pending' WHERE user_id = ?", (target_id,))
            conn.commit()
            conn.close()
            
            # Send payment request to user
            keyboard = [
                [InlineKeyboardButton("💰 Pay with Binance", callback_data='pay_binance')],
                [InlineKeyboardButton("📱 Pay with Easypaisa", callback_data='pay_easypaisa')]
            ]
            
            await context.bot.send_message(
                chat_id=target_id,
                text=f"🎉 APPROVED! Pay {MEMBERSHIP_FEE}:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            # 🔥 REMOVE BUTTONS - Show completed message
            await query.edit_message_text(
                f"✅ APPROVED SUCCESSFULLY!\n\n"
                f"User: {target_id}\n"
                f"Status: Payment request sent\n"
                f"Action: COMPLETED ✅\n\n"
                f"⏳ Waiting for user to complete payment..."
            )
            
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {e}")
        return
    
    # Admin reject - REMOVE BUTTONS AFTER CLICK
    if data.startswith('reject_'):
        try:
            target_id = int(data.split('_')[1])
            context.user_data['reject_id'] = target_id
            
            # 🔥 REMOVE BUTTONS - Show input request
            await query.edit_message_text(
                f"❌ REJECTING APPLICATION\n\n"
                f"User: {target_id}\n\n"
                f"Please type the rejection reason:\n"
                f"(This will be sent to user)"
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {e}")
        return
    
    # Final approve - REMOVE BUTTONS AFTER CLICK
    if data.startswith('final_'):
        try:
            target_id = int(data.split('_')[1])
            
            # Update database
            conn = get_db()
            c = conn.cursor()
            c.execute("UPDATE users SET status = 'completed' WHERE user_id = ?", (target_id,))
            conn.commit()
            conn.close()
            
            # Send links to user
            await context.bot.send_message(
                chat_id=target_id,
                text=f"🎉 PAYMENT VERIFIED!\n\n🔗 Telegram: {TELEGRAM_GROUP_LINK}\n📱 WhatsApp: {WHATSAPP_GROUP_LINK}"
            )
            
            # 🔥 REMOVE BUTTONS - Show completed
            await query.edit_message_text(
                f"✅ PAYMENT APPROVED!\n\n"
                f"User: {target_id}\n"
                f"Status: COMPLETED ✅\n"
                f"Links sent to user\n\n"
                f"🎉 User is now a premium member!"
            )
            
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {e}")
        return
    
    # Reject payment - REMOVE BUTTONS AFTER CLICK
    if data.startswith('rejectpay_'):
        try:
            target_id = int(data.split('_')[1])
            context.user_data['reject_id'] = target_id
            
            # 🔥 REMOVE BUTTONS - Show input request
            await query.edit_message_text(
                f"❌ REJECTING PAYMENT\n\n"
                f"User: {target_id}\n\n"
                f"Please type the rejection reason:\n"
                f"(This will be sent to user)"
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {e}")
        return

async def handle_text(update: Update, context):
    user_id = update.effective_user.id
    text = update.message.text
    
    user_data = get_user(user_id)
    if not user_data:
        await update.message.reply_text("Send /start to begin")
        return
    
    step = user_data[7]
    
    # Name
    if step == 'name_pending':
        if len(text) < 3:
            await update.message.reply_text("❌ Name too short! Enter FULL NAME:")
            return
        
        update_user(user_id, 'full_name', text)
        update_user(user_id, 'current_step', 'email_pending')
        
        await update.message.reply_text(EMAIL_MESSAGE.format(name=text))
        return
    
    # Email
    if step == 'email_pending':
        email = text.lower().strip()
        if "@" not in email:
            await update.message.reply_text("❌ Invalid email! Try again:")
            return
        
        update_user(user_id, 'email', email)
        update_user(user_id, 'current_step', 'proof_pending')
        
        request_type = user_data[5] or "purchase"
        await update.message.reply_text(PROOF_MESSAGE.format(type=request_type))
        return
    
    # WhatsApp - NOTIFY ADMIN
    if step == 'whatsapp_pending':
        clean = re.sub(r'[\s\-\(\)\.]', '', text)
        if not re.match(r'^\+\d{10,15}$', clean):
            await update.message.reply_text("❌ Invalid! Use: +923001234567")
            return
        
        # Save
        update_user(user_id, 'whatsapp', clean)
        update_user(user_id, 'current_step', 'info_submitted')
        
        # Confirm to user
        await update.message.reply_text(SUBMITTED_MESSAGE)
        
        # 🔥 NOTIFY ADMIN - PLAIN TEXT (NO MARKDOWN ERRORS)
        time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        admin_text = get_admin_notification(
            user_id=user_id,
            username=user_data[1],
            request_type=user_data[5],
            full_name=user_data[2],
            email=user_data[3],
            whatsapp=clean,
            time_now=time_now
