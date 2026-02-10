import logging
import sqlite3
import hashlib
import re
import os
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from telegram.constants import ParseMode

# ============= YOUR DETAILS =============
BOT_TOKEN = "8535390425:AAF67T7kjqxYxmjQTFhCH_l_6RnT_aB5frg"
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

# ============= PROFESSIONAL MESSAGES =============

WELCOME_MESSAGE = """
🎉 *Welcome to Premium Support Bot!* 🎉

Hello {name}! 👋

This is your gateway to exclusive premium content and live learning sessions.

📚 *What You'll Get:*
• Full support for all purchases
• Weekly live sessions (Sunday 10 PM PK)
• Instant updates on new content
• Lifetime access to premium group

💎 *Membership Fee:* {fee}

👇 *Please select what you purchased:*
"""

TYPE_SELECTED_MESSAGE = """
✅ *Great Choice!* ✅

You selected: *{type}*

📋 *Next Steps:*
We'll collect some information to verify your purchase and add you to our premium community.

📝 *Step 1 of 4: Personal Information*

Please enter your *FULL NAME* (as it appears on your ID):

_Example: Muhammad Ahmed Khan_
"""

NAME_RECEIVED_MESSAGE = """
✅ *Thank you, {name}!* ✅

📧 *Step 2 of 4: Contact Information*

Please enter your *EMAIL ADDRESS*:

_Example: yourname@gmail.com_

⚠️ *Important:* This email will be used for all communications.
"""

EMAIL_RECEIVED_MESSAGE = """
✅ *Email Saved!* ✅

📸 *Step 3 of 4: Purchase Verification*

Please upload a *CLEAR SCREENSHOT* of your {type} receipt/proof.

📋 *Screenshot should show:*
• Purchase/subscription details
• Payment confirmation
• Date and time of purchase
• Your name or email (if visible)

⚠️ *Note:* Blurry or fake screenshots will result in permanent ban.
"""

PROOF_RECEIVED_MESSAGE = """
✅ *Proof Received!* ✅

📱 *Step 4 of 4: WhatsApp Number*

Please enter your *WHATSAPP NUMBER* with country code:

🌍 *Format Examples:*
• Pakistan: *+923001234567*
• USA: *+14155552671*
• UK: *+447911123456*
• UAE: *+971501234567*

💬 *Why we need this:*
For instant support and live session reminders.
"""

SUBMITTED_MESSAGE = """
🎊 *Application Submitted Successfully!* 🎊

✅ Your information has been sent to our admin team.

⏳ *What happens next?*
• Admin will review your application within 24 hours
• You'll receive approval notification here
• Then you can complete payment to join

📊 *Your Application Status:* PENDING REVIEW

🔔 *You'll be notified as soon as admin approves!*

⚠️ *Please do not send multiple applications.*
"""

ADMIN_NOTIFICATION = """
🚨 *NEW APPLICATION RECEIVED* 🚨

📋 *Application Details:*
━━━━━━━━━━━━━━━━━━━━━
👤 *Username:* @{username}
🆔 *User ID:* `{user_id}`
📌 *Type:* {request_type}
━━━━━━━━━━━━━━━━━━━━━
📝 *Personal Info:*
• Name: {full_name}
• Email: {email}
📱 *WhatsApp:* {whatsapp}
━━━━━━━━━━━━━━━━━━━━━
⏰ *Submitted:* {time}

👇 *Please review and take action:*
"""

PAYMENT_REQUEST_MESSAGE = """
🎉 *CONGRATULATIONS! APPROVED!* 🎉

✅ *Admin has reviewed and APPROVED your application!*

💎 *You're one step away from joining our Premium Community!*

━━━━━━━━━━━━━━━━━━━━━
💳 *PAYMENT DETAILS*
━━━━━━━━━━━━━━━━━━━━━
*Amount:* {fee}
*Type:* Lifetime Membership

👇 *Select your preferred payment method:*
"""

PAYMENT_CONFIRMED_MESSAGE = """
⏳ *Payment Screenshot Received!* ⏳

✅ Your payment proof has been submitted for verification.

🕐 *Verification Time:* Usually within 2-4 hours

📊 *Status:* UNDER ADMIN REVIEW

⚠️ *Important:*
• Fake screenshots = Permanent ban
• You'll receive group links once verified
• Keep your notification on!

🔔 *You'll be notified soon!*
"""

ADMIN_PAYMENT_NOTIFICATION = """
💰 *NEW PAYMENT FOR VERIFICATION* 💰

👤 *User:* @{username}
🆔 *ID:* `{user_id}`
📝 *Name:* {full_name}
📧 *Email:* {email}
📱 *WhatsApp:* {whatsapp}
💳 *Method:* {method}
⏰ *Received:* {time}

👇 *Please verify payment and take action:*
"""

SUCCESS_MESSAGE = """
🎊 *PAYMENT VERIFIED! WELCOME!* 🎊

✅ *Your payment has been successfully verified!*

🎉 *You are now a Premium Member!*

━━━━━━━━━━━━━━━━━━━━━
🔗 *YOUR ACCESS LINKS*
━━━━━━━━━━━━━━━━━━━━━

📱 *Telegram Premium Group:*
{telegram_link}

💬 *WhatsApp Group:*
{whatsapp_link}

━━━━━━━━━━━━━━━━━━━━━
📅 *Live Sessions:*
Every Sunday at 10:00 PM Pakistan Time
Platform: GoTo Meeting App

⚠️ *IMPORTANT RULES:*
• ❌ Do NOT share these links with anyone
• ❌ Do NOT add fake members
• ✅ Follow all group rules
• ✅ Be respectful to all members

🚀 *Welcome to the Premium Family!*
🎓 *Start your learning journey now!*

💬 *Need help?* Contact admin anytime!
"""

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
            WELCOME_MESSAGE.format(name=first_name, fee=MEMBERSHIP_FEE),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    status = user_data[11]
    admin_approved = user_data[12]
    step = user_data[7]
    
    if status == 'completed':
        await update.message.reply_text(
            f"✅ *Welcome back {first_name}!*\n\nYou already have premium access.\n\n"
            f"🔗 *Telegram:* {TELEGRAM_GROUP_LINK}\n"
            f"📱 *WhatsApp:* {WHATSAPP_GROUP_LINK}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if admin_approved == 1 and status == 'payment_pending':
        keyboard = [
            [InlineKeyboardButton("💰 Pay with Binance", callback_data='pay_binance')],
            [InlineKeyboardButton("📱 Pay with Easypaisa", callback_data='pay_easypaisa')]
        ]
        await update.message.reply_text(
            f"⏰ *Payment Reminder*\n\n"
            f"✅ Your application is *APPROVED!*\n\n"
            f"💎 Complete payment to join:\n"
            f"💵 {MEMBERSHIP_FEE}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if step == 'info_submitted':
        await update.message.reply_text(
            "⏳ *Application Under Review*\n\n"
            "Your information has been submitted.\n"
            "Please wait for admin approval...",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if step == 'payment_submitted':
        await update.message.reply_text(
            "⏳ *Payment Verification in Progress*\n\n"
            "Admin is verifying your payment.\n"
            "You'll receive links soon!",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Resume
    if step == 'name_pending':
        await update.message.reply_text(
            f"🔄 *Continue Application*\n\n"
            f"📝 Please enter your *FULL NAME*:",
            parse_mode=ParseMode.MARKDOWN
        )
    elif step == 'email_pending':
        await update.message.reply_text(
            f"🔄 *Continue Application*\n\n"
            f"✅ Name: *{user_data[2]}*\n\n"
            f"📧 Please enter your *EMAIL*:",
            parse_mode=ParseMode.MARKDOWN
        )
    elif step == 'proof_pending':
        await update.message.reply_text(
            f"🔄 *Continue Application*\n\n"
            f"📸 Please upload your *PROOF SCREENSHOT*:",
            parse_mode=ParseMode.MARKDOWN
        )
    elif step == 'whatsapp_pending':
        await update.message.reply_text(
            f"🔄 *Continue Application*\n\n"
            f"📱 Please enter your *WHATSAPP NUMBER*:\n\n"
            f"_Example: +923001234567_",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        keyboard = [
            [InlineKeyboardButton("💎 Premium Subscription", callback_data='type_premium')],
            [InlineKeyboardButton("🛒 Product Purchase", callback_data='type_product')]
        ]
        await update.message.reply_text(
            WELCOME_MESSAGE.format(name=first_name, fee=MEMBERSHIP_FEE),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
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
        
        await query.edit_message_text(
            TYPE_SELECTED_MESSAGE.format(type=request_type),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Payment selection
    if data.startswith('pay_'):
        method = data.split('_')[1]
        update_user(user_id, 'payment_method', method.capitalize())
        
        if method == 'binance':
            text = f"""
💰 *BINANCE PAYMENT*

📧 *Email:* `{BINANCE_EMAIL}`
🆔 *Binance ID:* `{BINANCE_ID}`
🌐 *Network:* `{BINANCE_NETWORK}`
💵 *Amount:* {MEMBERSHIP_FEE}

✅ *After payment, send screenshot here*
"""
        else:
            text = f"""
📱 *EASYPAYSA PAYMENT*

👤 *Account Name:* {EASYPAYSA_NAME}
📞 *Account Number:* `{EASYPAYSA_NUMBER}`
💵 *Amount:* {MEMBERSHIP_FEE}

✅ *After payment, send screenshot here*
"""
        
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        return
    
    # Admin approve application
    if data.startswith('approve_'):
        try:
            target_id = int(data.split('_')[1])
            
            conn = get_db()
            c = conn.cursor()
            c.execute("UPDATE users SET admin_approved = 1, status = 'payment_pending', current_step = 'payment_pending' WHERE user_id = ?", (target_id,))
            conn.commit()
            conn.close()
            
            keyboard = [
                [InlineKeyboardButton("💰 Pay with Binance", callback_data='pay_binance')],
                [InlineKeyboardButton("📱 Pay with Easypaisa", callback_data='pay_easypaisa')]
            ]
            
            await context.bot.send_message(
                chat_id=target_id,
                text=PAYMENT_REQUEST_MESSAGE.format(fee=MEMBERSHIP_FEE),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            
            await query.edit_message_text(
                f"✅ *APPROVED SUCCESSFULLY!*\n\n"
                f"User `{target_id}` has been notified to complete payment.\n\n"
                f"📨 Payment request sent!",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {e}")
        return
    
    # Admin reject application
    if data.startswith('reject_'):
        try:
            target_id = int(data.split('_')[1])
            context.user_data['reject_id'] = target_id
            
            await query.edit_message_text(
                f"❌ *Rejecting Application*\n\n"
                f"User ID: `{target_id}`\n\n"
                f"Please type the rejection reason:",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {e}")
        return
    
    # FINAL APPROVE - Send links
    if data.startswith('final_'):
        try:
            target_id = int(data.split('_')[1])
            
            conn = get_db()
            c = conn.cursor()
            c.execute("UPDATE users SET status = 'completed' WHERE user_id = ?", (target_id,))
            conn.commit()
            conn.close()
            
            await context.bot.send_message(
                chat_id=target_id,
                text=SUCCESS_MESSAGE.format(
                    telegram_link=TELEGRAM_GROUP_LINK,
                    whatsapp_link=WHATSAPP_GROUP_LINK
                ),
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=False
            )
            
            await query.edit_message_text(
                f"✅ *PAYMENT APPROVED!*\n\n"
                f"User `{target_id}` has been verified.\n"
                f"🎉 Group links sent successfully!\n\n"
                f"Status: COMPLETED ✅",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {e}")
        return
    
    # Reject payment
    if data.startswith('rejectpay_'):
        try:
            target_id = int(data.split('_')[1])
            context.user_data['reject_id'] = target_id
            
            await query.edit_message_text(
                f"❌ *Rejecting Payment*\n\n"
                f"User ID: `{target_id}`\n\n"
                f"Please type the rejection reason:",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {e}")
        return

async def handle_text(update: Update, context):
    user_id = update.effective_user.id
    text = update.message.text
    
    user_data = get_user(user_id)
    if not user_data:
        await update.message.reply_text("Please send /start to begin")
        return
    
    step = user_data[7]
    
    # Name
    if step == 'name_pending':
        if len(text) < 3:
            await update.message.reply_text(
                "❌ *Name too short!*\n\nPlease enter your *FULL NAME*:",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        update_user(user_id, 'full_name', text)
        update_user(user_id, 'current_step', 'email_pending')
        
        await update.message.reply_text(
            NAME_RECEIVED_MESSAGE.format(name=text),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Email
    if step == 'email_pending':
        email = text.lower().strip()
        if "@" not in email or "." not in email:
            await update.message.reply_text(
                "❌ *Invalid Email!*\n\nPlease enter a valid email address:\n\n_Example: yourname@gmail.com_",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        update_user(user_id, 'email', email)
        update_user(user_id, 'current_step', 'proof_pending')
        
        request_type = user_data[5] or "purchase"
        await update.message.reply_text(
            EMAIL_RECEIVED_MESSAGE.format(type=request_type),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # WhatsApp
    if step == 'whatsapp_pending':
        clean = re.sub(r'[\s\-\(\)\.]', '', text)
        if not re.match(r'^\+\d{10,15}$', clean):
            await update.message.reply_text(
                "❌ *Invalid Number!*\n\nPlease enter with country code:\n\n"
                "• Pakistan: `+923001234567`\n"
                "• USA: `+14155552671`\n"
                "• UK: `+447911123456`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        update_user(user_id, 'whatsapp', clean)
        update_user(user_id, 'current_step', 'info_submitted')
        
        # Send confirmation to user
        await update.message.reply_text(
            SUBMITTED_MESSAGE,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Send detailed notification to admin
        time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        keyboard = [
            [
                InlineKeyboardButton("✅ APPROVE", callback_data=f'approve_{user_id}'),
                InlineKeyboardButton("❌ REJECT", callback_data=f'reject_{user_id}')
            ]
        ]
        
        admin_msg = ADMIN_NOTIFICATION.format(
            username=user_data[1],
            user_id=user_id,
            request_type=user_data[5],
            full_name=user_data[2],
            email=user_data[3],
            whatsapp=clean,
            time=time_now
        )
        
        if user_data[6]:  # proof exists
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=user_data[6],
                caption=admin_msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        return
    
    # Rejection reason
    if 'reject_id' in context.user_data:
        target_id = context.user_data['reject_id']
        
        await context.bot.send_message(
            chat_id=target_id,
            text=f"""
❌ *APPLICATION REJECTED*

Your application has been rejected.

*Reason:* {text}

If you think this is a mistake, please contact admin or send /start to apply again.
""",
            parse_mode=ParseMode.MARKDOWN
        )
        
        await update.message.reply_text(
            f"❌ *User {target_id} has been rejected.*\n\nReason sent to user.",
            parse_mode=ParseMode.MARKDOWN
        )
        
        del context.user_data['reject_id']
        return

async def handle_photo(update: Update, context):
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
            PROOF_RECEIVED_MESSAGE,
            parse_mode=ParseMode.MARKDOWN
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
                "🚫 *DUPLICATE SCREENSHOT DETECTED!*\n\nThis screenshot has already been used.",
                parse_mode=ParseMode.MARKDOWN
            )
            conn.close()
            return
        
        c.execute("INSERT INTO screenshots (file_hash, user_id, used_at) VALUES (?, ?, ?)", (hash_val, user_id, datetime.now()))
        c.execute("UPDATE users SET payment_file_id = ?, payment_hash = ?, current_step = 'payment_submitted', status = 'payment_verification' WHERE user_id = ?",
                  (photo.file_id, hash_val, user_id))
        conn.commit()
        conn.close()
        
        # Confirm to user
        await update.message.reply_text(
            PAYMENT_CONFIRMED_MESSAGE,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Send to admin with BIG buttons
        time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        keyboard = [
            [
                InlineKeyboardButton("✅ APPROVE & SEND LINKS", callback_data=f'final_{user_id}'),
                InlineKeyboardButton("❌ REJECT PAYMENT", callback_data=f'rejectpay_{user_id}')
            ]
        ]
        
        admin_msg = ADMIN_PAYMENT_NOTIFICATION.format(
            username=user_data[1],
            user_id=user_id,
            full_name=user_data[2],
            email=user_data[3],
            whatsapp=user_data[4],
            method=user_data[8] or "Not specified",
            time=time_now
        )
        
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo.file_id,
            caption=admin_msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        return

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("🤖 Professional Bot Started!")
    print("✅ All messages are professional and clear")
    application.run_polling()

if __name__ == '__main__':
    main()
