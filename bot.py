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

# ============= LUXURY UI =============

class LuxuryUI:
    EMOJIS = {
        'crown': '👑', 'diamond': '💎', 'star': '⭐', 'sparkles': '✨',
        'fire': '🔥', 'rocket': '🚀', 'shield': '🛡️', 'key': '🔐',
        'vip': '🎖️', 'medal': '🏆', 'money_bag': '💰', 'phone': '📱',
        'email': '📧', 'id': '🆔', 'check': '✅', 'cross': '❌',
        'warning': '⚠️', 'info': 'ℹ️', 'clock': '⏰', 'hourglass': '⏳',
        'bullet': '•', 'arrow': '➤', 'divider': '━━━━━━━━━━━━━━━'
    }
    
    @staticmethod
    def button(text, callback_data, emoji='💎'):
        return InlineKeyboardButton(f"{emoji} {text}", callback_data=callback_data)
    
    @staticmethod
    def box(title, content, width=40):
        top = f"╔{'═' * (width-2)}╗"
        title_line = f"║{title.center(width-2)}║"
        sep = f"╠{'═' * (width-2)}╣"
        bottom = f"╚{'═' * (width-2)}╝"
        
        lines = []
        for line in content.split('\n'):
            if len(line) > width-4:
                line = line[:width-7] + "..."
            lines.append(f"║ {line.ljust(width-4)} ║")
        
        return f"{top}\n{title_line}\n{sep}\n" + '\n'.join(lines) + f"\n{bottom}"

# ============= MESSAGE TEMPLATES =============

class Messages:
    
    @staticmethod
    def welcome(first_name):
        return f"""
{LuxuryUI.EMOJIS['crown']} <b>PREMIUM SUPPORT BOT</b> {LuxuryUI.EMOJIS['crown']}

Assalam-o-Alaikum, <b>{first_name}</b>!

{LuxuryUI.box('WELCOME MESSAGE', '''Premium support ke liye hum aap ko welcome karte hain. Agar aap hamari Premium community ke andar join hona chahte hain, to hum aap se kuch information lenge.

Jaldbaazi mein galat information submit na karein. Agar form reject ho gaya, to dobara apply nahi kar saken ge.

Community mein aap ko complete premium support milegi. Har Sunday raat ko live class hogi jisme aap ke issues solve honge.''')}

{LuxuryUI.EMOJIS['arrow']} <b>Select membership type:</b>
"""
    
    @staticmethod
    def step(step_num, total, title, instruction):
        return f"""
{LuxuryUI.EMOJIS['diamond']} <b>STEP {step_num}/{total}: {title}</b> {LuxuryUI.EMOJIS['diamond']}

{LuxuryUI.EMOJIS['divider']}

{instruction}

{LuxuryUI.EMOJIS['warning']} <i>Galat information se form reject ho sakta hai</i>
"""
    
    @staticmethod
    def payment_binance():
        return f"""
{LuxuryUI.EMOJIS['money_bag']} <b>PAYMENT DETAILS - BINANCE</b> {LuxuryUI.EMOJIS['money_bag']}

{LuxuryUI.box('TRANSFER INFO', f'''
Amount: {MEMBERSHIP_FEE}
Network: TRC20

Email: {BINANCE_EMAIL}
ID: {BINANCE_ID}

Status: Waiting...
''')}

{LuxuryUI.EMOJIS['warning']} Exact amount bhejein
{LuxuryUI.EMOJIS['info']} Payment ke baad screenshot bhejein
"""
    
    @staticmethod
    def payment_easypaisa():
        return f"""
{LuxuryUI.EMOJIS['phone']} <b>PAYMENT DETAILS - EASYPAYSA</b> {LuxuryUI.EMOJIS['phone']}

{LuxuryUI.box('TRANSFER INFO', f'''
Amount: {MEMBERSHIP_FEE}

Name: {EASYPAYSA_NAME}
Number: {EASYPAYSA_NUMBER}

Status: Waiting...
''')}

{LuxuryUI.EMOJIS['warning']} Exact amount bhejein
{LuxuryUI.EMOJIS['info']} Payment ke baad screenshot bhejein
"""
    
    @staticmethod
    def approved():
        return f"""
{LuxuryUI.EMOJIS['medal']} <b>MUBARAK HO! APPROVED</b> {LuxuryUI.EMOJIS['medal']}

{LuxuryUI.EMOJIS['check']} Aap ka application approve ho gaya hai!

Ab aap ne payment complete karni hai. Neeche options select karein:
"""
    
    @staticmethod
    def verifying():
        return f"""
{LuxuryUI.EMOJIS['clock']} <b>PAYMENT VERIFY HO RAHI HAI</b> {LuxuryUI.EMOJIS['clock']}

{LuxuryUI.EMOJIS['divider']}

Aap ki payment receive ho gayi hai.
Verification process mein 5-10 minute lagenge.

{LuxuryUI.EMOJIS['info']} Bar bar message na karein
"""
    
    @staticmethod
    def access_granted():
        return f"""
{LuxuryUI.EMOJIS['trophy']} <b>WELCOME TO ELITE CIRCLE!</b> {LuxuryUI.EMOJIS['trophy']}

{LuxuryUI.EMOJIS['fire']} Aap ko premium access mil gaya hai! {LuxuryUI.EMOJIS['fire']}

{LuxuryUI.box('YOUR ACCESS LINKS', f'''
TELEGRAM GROUP:
{TELEGRAM_GROUP_LINK}

WHATSAPP GROUP:
{WHATSAPP_GROUP_LINK}

SUNDAY LIVE CLASS:
Raat ko timings announce ki jayengi
''')}

{LuxuryUI.EMOJIS['shield']} Links share karne par ban hoga
{LuxuryUI.EMOJIS['rocket']} Aap ki journey shuru ho gayi hai!
"""
    
    @staticmethod
    def admin_new_application(user_data, whatsapp):
        return f"""
{LuxuryUI.EMOJIS['star']} <b>NEW APPLICATION</b> {LuxuryUI.EMOJIS['star']}

{LuxuryUI.EMOJIS['divider']}

<b>User:</b> @{user_data[1] or 'N/A'}
<b>ID:</b> <code>{user_data[0]}</code>
<b>Name:</b> {user_data[2]}
<b>Email:</b> {user_data[3]}
<b>WhatsApp:</b> <code>{whatsapp}</code>
<b>Type:</b> {user_data[5]}

{LuxuryUI.EMOJIS['divider']}

<i>Review and approve:</i>
"""
    
    @staticmethod
    def admin_payment_verify(user_data):
        return f"""
{LuxuryUI.EMOJIS['money_bag']} <b>PAYMENT VERIFICATION</b> {LuxuryUI.EMOJIS['money_bag']}

{LuxuryUI.EMOJIS['divider']}

<b>User:</b> @{user_data[1] or 'N/A'}
<b>ID:</b> <code>{user_data[0]}</code>
<b>Name:</b> {user_data[2]}
<b>Method:</b> {user_data[8]}

{LuxuryUI.EMOJIS['divider']}

<i>Verify payment:</i>
"""
    
    @staticmethod
    def action_taken(action, time_str=None):
        t = time_str or datetime.now().strftime('%H:%M:%S')
        if action == 'approved':
            return f"\n\n{LuxuryUI.EMOJIS['check']} <b>APPROVED</b> at {t}\nUser notified ✅"
        elif action == 'rejected':
            return f"\n\n{LuxuryUI.EMOJIS['cross']} <b>REJECTED</b> at {t}\nUser notified ✅"
        elif action == 'payment_verified':
            return f"\n\n{LuxuryUI.EMOJIS['medal']} <b>PAYMENT VERIFIED</b> at {t}\nAccess granted ✅"
        elif action == 'payment_rejected':
            return f"\n\n{LuxuryUI.EMOJIS['cross']} <b>PAYMENT REJECTED</b> at {t}"

# ============= BOT FUNCTIONS =============

async def start(update: Update, context):
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name
    
    user_data = get_user(user_id)
    
    if not user_data:
        create_user(user_id, user.username or "No username")
        
        keyboard = [
            [LuxuryUI.button("Premium Subscription", "premium", "👑")],
            [LuxuryUI.button("Product Purchase", "product", "🛒")]
        ]
        
        await update.message.reply_text(
            Messages.welcome(first_name),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    status = user_data[11]
    admin_approved = user_data[12]
    step = user_data[7]
    
    if status == 'completed':
        await update.message.reply_text(
            Messages.access_granted(),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        return
    
    if admin_approved == 1 and status == 'payment_pending':
        keyboard = [
            [LuxuryUI.button("Binance Pay", "binance", "💰")],
            [LuxuryUI.button("Easypaisa", "easypaisa", "📱")]
        ]
        
        await update.message.reply_text(
            Messages.approved(),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if step == 'info_submitted':
        await update.message.reply_text(
            f"""
{LuxuryUI.EMOJIS['hourglass']} <b>UNDER REVIEW</b>

Aap ka application review ho raha hai.
Approval ka intezaar karein.

{LuxuryUI.EMOJIS['clock']} Time: 5-15 minutes
""",
            parse_mode=ParseMode.HTML
        )
        return
    
    if step == 'payment_submitted':
        await update.message.reply_text(
            Messages.verifying(),
            parse_mode=ParseMode.HTML
        )
        return
    
    # Resume steps
    if step == 'name_pending':
        await update.message.reply_text(
            Messages.step(1, 4, "Personal Info", "Apna <b>full name</b> enter karein (jaisa ID card par hai):"),
            parse_mode=ParseMode.HTML
        )
    elif step == 'email_pending':
        await update.message.reply_text(
            Messages.step(2, 4, "Contact Details", f"Name: <b>{user_data[2]}</b>\n\nApna <b>email address</b> enter karein:"),
            parse_mode=ParseMode.HTML
        )
    elif step == 'proof_pending':
        await update.message.reply_text(
            Messages.step(3, 4, "Purchase Proof", "Apni <b>purchase receipt</b> ka screenshot upload karein:"),
            parse_mode=ParseMode.HTML
        )
    elif step == 'whatsapp_pending':
        await update.message.reply_text(
            Messages.step(4, 4, "Final Step", "Apna <b>WhatsApp number</b> enter karein with country code:\n<i>Example: +923001234567</i>"),
            parse_mode=ParseMode.HTML
        )
    else:
        keyboard = [
            [LuxuryUI.button("Premium Subscription", "premium", "👑")],
            [LuxuryUI.button("Product Purchase", "product", "🛒")]
        ]
        await update.message.reply_text(
            Messages.welcome(first_name),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    if data in ['premium', 'product']:
        request_type = "Premium Subscription" if data == 'premium' else "Product Purchase"
        update_user(user_id, 'request_type', request_type)
        update_user(user_id, 'current_step', 'name_pending')
        
        await query.edit_message_text(
            Messages.step(1, 4, "Personal Info", "Apna <b>full name</b> enter karein (jaisa ID card par hai):"),
            parse_mode=ParseMode.HTML
        )
        return
    
    if data in ['binance', 'easypaisa']:
        update_user(user_id, 'payment_method', data.capitalize())
        
        if data == 'binance':
            await query.edit_message_text(
                Messages.payment_binance(),
                parse_mode=ParseMode.HTML
            )
        else:
            await query.edit_message_text(
                Messages.payment_easypaisa(),
                parse_mode=ParseMode.HTML
            )
        return
    
    # Admin approve
    if data.startswith('approve_'):
        try:
            target_id = int(data.split('_')[1])
            
            conn = get_db()
            c = conn.cursor()
            c.execute("UPDATE users SET admin_approved = 1, status = 'payment_pending', current_step = 'payment_pending' WHERE user_id = ?", (target_id,))
            conn.commit()
            conn.close()
            
            # Remove buttons
            await query.edit_message_reply_markup(reply_markup=None)
            
            original = query.message.text or query.message.caption or ""
            updated = original + Messages.action_taken('approved')
            
            if query.message.photo:
                await query.edit_message_caption(caption=updated, parse_mode=ParseMode.HTML)
            else:
                await query.edit_message_text(updated, parse_mode=ParseMode.HTML)
            
            # Notify user
            keyboard = [
                [LuxuryUI.button("Binance Pay", "binance", "💰")],
                [LuxuryUI.button("Easypaisa", "easypaisa", "📱")]
            ]
            
            await context.bot.send_message(
                chat_id=target_id,
                text=Messages.approved(),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await query.edit_message_text(f"❌ Error: {e}")
        return
    
    # Admin reject
    if data.startswith('reject_'):
        try:
            target_id = int(data.split('_')[1])
            context.user_data['reject_id'] = target_id
            
            await query.edit_message_reply_markup(reply_markup=None)
            
            original = query.message.text or query.message.caption or ""
            updated = original + Messages.action_taken('rejected')
            
            if query.message.photo:
                await query.edit_message_caption(caption=updated, parse_mode=ParseMode.HTML)
            else:
                await query.edit_message_text(updated, parse_mode=ParseMode.HTML)
            
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"❌ Rejecting user {target_id}\n\nRejection reason type karein:"
            )
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await query.edit_message_text(f"❌ Error: {e}")
        return
    
    # Final approve
    if data.startswith('final_'):
        try:
            target_id = int(data.split('_')[1])
            
            conn = get_db()
            c = conn.cursor()
            c.execute("UPDATE users SET status = 'completed' WHERE user_id = ?", (target_id,))
            conn.commit()
            conn.close()
            
            await query.edit_message_reply_markup(reply_markup=None)
            
            original = query.message.caption or ""
            updated = original + Messages.action_taken('payment_verified')
            
            await query.edit_message_caption(caption=updated, parse_mode=ParseMode.HTML)
            
            await context.bot.send_message(
                chat_id=target_id,
                text=Messages.access_granted(),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await query.edit_message_text(f"❌ Error: {e}")
        return
    
    # Reject payment
    if data.startswith('rejectpay_'):
        try:
            target_id = int(data.split('_')[1])
            context.user_data['reject_id'] = target_id
            context.user_data['reject_payment'] = True
            
            await query.edit_message_reply_markup(reply_markup=None)
            
            original = query.message.caption or ""
            updated = original + Messages.action_taken('payment_rejected')
            
            await query.edit_message_caption(caption=updated, parse_mode=ParseMode.HTML)
            
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"❌ Reject payment {target_id}\n\nReason type karein:"
            )
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await query.edit_message_text(f"❌ Error: {e}")
        return

async def handle_text(update: Update, context):
    user_id = update.effective_user.id
    text = update.message.text
    
    user_data = get_user(user_id)
    if not user_data:
        await update.message.reply_text("Send /start")
        return
    
    step = user_data[7]
    
    # Name
    if step == 'name_pending':
        if len(text) < 2:
            await update.message.reply_text("❌ Name too short!")
            return
        
        update_user(user_id, 'full_name', text)
        update_user(user_id, 'current_step', 'email_pending')
        
        await update.message.reply_text(
            Messages.step(2, 4, "Contact Details", f"✅ Name: <b>{text}</b>\n\nApna <b>email</b> enter karein:"),
            parse_mode=ParseMode.HTML
        )
        return
    
    # Email
    if step == 'email_pending':
        if "@" not in text or "." not in text.split('@')[-1]:
            await update.message.reply_text("❌ Invalid email! Try again:")
            return
        
        update_user(user_id, 'email', text)
        update_user(user_id, 'current_step', 'proof_pending')
        
        await update.message.reply_text(
            Messages.step(3, 4, "Purchase Proof", f"✅ Email: <b>{text}</b>\n\n<b>Proof screenshot</b> upload karein:"),
            parse_mode=ParseMode.HTML
        )
        return
    
    # WhatsApp
    if step == 'whatsapp_pending':
        clean = re.sub(r'[\s\-\(\)\.]', '', text)
        if not re.match(r'^\+\d{10,15}$', clean):
            await update.message.reply_text("❌ Invalid! Format: +923001234567")
            return
        
        update_user(user_id, 'whatsapp', clean)
        update_user(user_id, 'current_step', 'info_submitted')
        
        await update.message.reply_text(
            f"""
{LuxuryUI.EMOJIS['check']} <b>SUBMITTED!</b>

Aap ka application admin review ke liye bhej diya gaya hai.
Approval ka intezaar karein.
""",
            parse_mode=ParseMode.HTML
        )
        
        # Send to admin
        keyboard = [
            [
                LuxuryUI.button("Approve", f"approve_{user_id}", "✅"),
                LuxuryUI.button("Reject", f"reject_{user_id}", "❌")
            ]
        ]
        
        admin_msg = Messages.admin_new_application(user_data, clean)
        
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
    
    # Rejection reason
    if 'reject_id' in context.user_data:
        target_id = context.user_data['reject_id']
        is_payment = context.user_data.get('reject_payment', False)
        
        header = "Payment Rejected" if is_payment else "Application Rejected"
        
        await context.bot.send_message(
            chat_id=target_id,
            text=f"""
{LuxuryUI.EMOJIS['cross']} <b>{header}</b>

Reason: <i>{text}</i>

Support se contact karein agar mistake lage.
"""
        )
        
        await update.message.reply_text(f"✅ User {target_id} notified.")
        
        del context.user_data['reject_id']
        if 'reject_payment' in context.user_data:
            del context.user_data['reject_payment']
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
            Messages.step(4, 4, "Final Step", "✅ Proof received!\n\n<b>WhatsApp number</b> enter karein (+923001234567):"),
            parse_mode=ParseMode.HTML
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
                f"""
{LuxuryUI.EMOJIS['cross']} <b>DUPLICATE SCREENSHOT!</b>

Yeh screenshot pehle use ho chuka hai.
New screenshot bhejein.
"""
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
            Messages.verifying(),
            parse_mode=ParseMode.HTML
        )
        
        # Send to admin
        keyboard = [
            [
                LuxuryUI.button("Verify & Grant Access", f"final_{user_id}", "🏆"),
                LuxuryUI.button("Reject Payment", f"rejectpay_{user_id}", "🚫")
            ]
        ]
        
        admin_msg = Messages.admin_payment_verify(user_data)
        
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo.file_id,
            caption=admin_msg,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("""
    ╔══════════════════════════════════════╗
    ║     👑 PREMIUM BOT ACTIVATED 👑      ║
    ║         Railway Ready                ║
    ╚══════════════════════════════════════╝
    """)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
