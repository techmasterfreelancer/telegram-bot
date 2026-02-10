import logging
import sqlite3
import hashlib
import re
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.constants import ParseMode
from gtts import gTTS
import tempfile

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

# VOICE SCRIPTS - Aapki provided text
VOICE_SCRIPTS = {
    'welcome': """Premium support ke liye hum aap ko welcome karte hain. Agar aap log hamari Premium community ke andar join hona chahte hain, to is ke liye hum aap se kuch information lenge. Is silsile mein aap ko hamare saath cooperate karna hoga.

Jaldbaazi mein koi bhi information galat upload ya submit na karein. Kyun ke agar ek dafa aap ka form reject ho gaya, to phir mumkin nahi hoga ke hum aap ko dobara add kar saken. Kyun ke aap ko yahin se group joining milegi.

Doosri sab se important baat yeh hai ke jab hum aap ko community ke andar join karwa denge, to wahan aap ko complete premium support milegi. Aap ke jo bhi issues honge, hum un ko solve out karwayenge.

Saath hi saath hamari taraf se aap ke liye ek badi opportunity bhi hogi ke har week Sunday ke din raat ko hum aap ki live class liya karenge. Proper tareeke se aap ke saath baat cheet hogi, aap ke issues sune jayenge aur aap ko un ka solution diya jayega.

Ab hamara jo bot hai, aap ne Start par click karna hai aur phir aage apni information waghera fill up karte jana hai. Thank you so much.""",
    
    'step1_name': "Step number one. Apna full name enter karein, jaisa ke aap ke ID card par likha hua hai. Galat name enter karne se aap ka form reject ho sakta hai.",
    
    'step2_email': "Step number two. Ab apna email address enter karein. Yeh wohi email honi chahiye jis se aap hamare saath contact mein reh saken. Example: aapkaemail@gmail.com",
    
    'step3_proof': "Step number three. Ab aap ne apni purchase ki proof upload karni hai. Screenshot clear hona chahiye jis mein date aur time visible ho. Blur ya fake screenshot se aap ka form reject ho jayega.",
    
    'step4_whatsapp': "Step number four. Final step. Apna WhatsApp number enter karein with country code. Example: plus nine two three zero zero one two three four five six seven. Is number par aap ko updates milengi.",
    
    'approved': "Mubarak ho! Aap ka application approve ho gaya hai. Ab aap ne payment complete karni hai. Payment ke options aap ko screen par nazar aa rahe hain. Payment ke baad screenshot zaroor bhejein.",
    
    'payment_received': "Aap ki payment receive ho gayi hai. Ab aap ki payment verify ho rahi hai. Yeh process 5 se 10 minute lag sakta hai. Aap ko jald hi access mil jayega. Bar bar message na karein.",
    
    'access_granted': "Congratulations! Aap ko premium community ka access mil gaya hai. Aap ko Telegram group aur WhatsApp group ke links bhej diye gaye hain. Sunday ki live class ka intezaar karein. Welcome to the family!",
    
    'rejected': "Afsos, aap ka form reject kar diya gaya hai. Jo reason diya gaya hai woh aap ne parh liya hoga. Ab aap dobara apply nahi kar saken ge. Agar koi mistake ho to admin se contact karein.",
    
    'duplicate_screenshot': "Warning! Yeh screenshot pehle se use ho chuka hai. Aap ne new aur original screenshot bhejni hai. Duplicate screenshot se aap ka account ban ho sakta hai."
}

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

# ============= VOICE GENERATION =============

def generate_voice(text, filename=None):
    """Generate voice file from text using gTTS"""
    try:
        if filename is None:
            # Create temp file
            temp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            filename = temp.name
        
        # Generate Hindi/Urdu mixed voice (en for English, hi for Hindi/Urdu words)
        tts = gTTS(text=text, lang='hi', slow=False)
        tts.save(filename)
        return filename
    except Exception as e:
        logger.error(f"Voice generation error: {e}")
        return None

async def send_voice_message(update_or_context, chat_id, text_key, text_override=None):
    """Send voice message with text"""
    try:
        text = text_override or VOICE_SCRIPTS.get(text_key, "")
        if not text:
            return
        
        # Generate voice
        voice_file = generate_voice(text)
        if voice_file and os.path.exists(voice_file):
            # Send voice
            if hasattr(update_or_context, 'message'):
                # It's an update object
                await update_or_context.message.reply_voice(voice=InputFile(voice_file))
            else:
                # It's context.bot
                await update_or_context.send_voice(chat_id=chat_id, voice=InputFile(voice_file))
            
            # Cleanup temp file
            try:
                os.remove(voice_file)
            except:
                pass
    except Exception as e:
        logger.error(f"Error sending voice: {e}")

# ============= LUXURY UI =============

class LuxuryUI:
    EMOJIS = {
        'crown': '👑', 'diamond': '💎', 'star': '⭐', 'sparkles': '✨',
        'fire': '🔥', 'rocket': '🚀', 'shield': '🛡️', 'key': '🔐',
        'vip': '🎖️', 'medal': '🏆', 'money_bag': '💰', 'phone': '📱',
        'email': '📧', 'id': '🆔', 'check': '✅', 'cross': '❌',
        'warning': '⚠️', 'info': 'ℹ️', 'clock': '⏰', 'hourglass': '⏳',
        'mic': '🎙️', 'speaker': '🔊'
    }
    
    @staticmethod
    def button(text, callback_data, emoji='💎'):
        return InlineKeyboardButton(f"{emoji} {text}", callback_data=callback_data)

# ============= BOT FUNCTIONS =============

async def start(update: Update, context):
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name
    
    user_data = get_user(user_id)
    
    if not user_data:
        create_user(user_id, user.username or "No username")
        
        # 🎙️ STEP 1: Send WELCOME VOICE FIRST
        await send_voice_message(update, user_id, 'welcome')
        
        # Then send text with buttons
        keyboard = [
            [LuxuryUI.button("Premium Subscription", "premium", "👑")],
            [LuxuryUI.button("Product Purchase", "product", "🛒")]
        ]
        
        welcome_text = f"""
{LuxuryUI.EMOJIS['crown']} <b>PREMIUM SUPPORT BOT</b> {LuxuryUI.EMOJIS['crown']}

🔊 <i>Above is your welcome message. Please listen carefully.</i>

{LuxuryUI.EMOJIS['divider']}

<b>Select your membership type:</b>
"""
        
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # ... rest of existing logic with voice additions
    status = user_data[11]
    admin_approved = user_data[12]
    step = user_data[7]
    
    if status == 'completed':
        await send_voice_message(update, user_id, 'access_granted')
        await update.message.reply_text(
            f"{LuxuryUI.EMOJIS['medal']} You have full access!",
            parse_mode=ParseMode.HTML
        )
        return
    
    if admin_approved == 1 and status == 'payment_pending':
        await send_voice_message(update, user_id, 'approved')
        
        keyboard = [
            [LuxuryUI.button("Binance Pay", "binance", "💰")],
            [LuxuryUI.button("Easypaisa", "easypaisa", "📱")]
        ]
        
        await update.message.reply_text(
            "Select payment method:",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Resume steps with voice
    if step == 'name_pending':
        await send_voice_message(update, user_id, 'step1_name')
        await update.message.reply_text(
            f"{LuxuryUI.EMOJIS['user']} Enter your full name:",
            parse_mode=ParseMode.HTML
        )
    elif step == 'email_pending':
        await send_voice_message(update, user_id, 'step2_email')
        await update.message.reply_text(
            f"{LuxuryUI.EMOJIS['email']} Enter your email:",
            parse_mode=ParseMode.HTML
        )
    elif step == 'proof_pending':
        await send_voice_message(update, user_id, 'step3_proof')
        await update.message.reply_text(
            f"{LuxuryUI.EMOJIS['check']} Upload proof screenshot:",
            parse_mode=ParseMode.HTML
        )
    elif step == 'whatsapp_pending':
        await send_voice_message(update, user_id, 'step4_whatsapp')
        await update.message.reply_text(
            f"{LuxuryUI.EMOJIS['phone']} Enter WhatsApp (+923001234567):",
            parse_mode=ParseMode.HTML
        )
    else:
        keyboard = [
            [LuxuryUI.button("Premium Subscription", "premium", "👑")],
            [LuxuryUI.button("Product Purchase", "product", "🛒")]
        ]
        await update.message.reply_text(
            "Welcome! Select type:",
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
        
        # Voice for name step
        await context.bot.send_voice(chat_id=user_id, voice=InputFile(generate_voice(VOICE_SCRIPTS['step1_name'])))
        
        await query.edit_message_text(
            f"{LuxuryUI.EMOJIS['user']} <b>Step 1/4:</b> Enter your full name:",
            parse_mode=ParseMode.HTML
        )
        return
    
    if data in ['binance', 'easypaisa']:
        update_user(user_id, 'payment_method', data.capitalize())
        
        if data == 'binance':
            text = f"💰 <b>BINANCE:</b>\n<code>{BINANCE_EMAIL}</code>\nID: <code>{BINANCE_ID}</code>"
        else:
            text = f"📱 <b>EASYPAYSA:</b>\nName: {EASYPAYSA_NAME}\n<code>{EASYPAYSA_NUMBER}</code>"
        
        await query.edit_message_text(text, parse_mode=ParseMode.HTML)
        return
    
    # Admin approve
    if data.startswith('approve_'):
        target_id = int(data.split('_')[1])
        
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE users SET admin_approved = 1, status = 'payment_pending', current_step = 'payment_pending' WHERE user_id = ?", (target_id,))
        conn.commit()
        conn.close()
        
        # Remove buttons
        await query.edit_message_reply_markup(reply_markup=None)
        
        # Voice to user
        await context.bot.send_voice(chat_id=target_id, voice=InputFile(generate_voice(VOICE_SCRIPTS['approved'])))
        
        keyboard = [
            [LuxuryUI.button("Binance Pay", "binance", "💰")],
            [LuxuryUI.button("Easypaisa", "easypaisa", "📱")]
        ]
        
        await context.bot.send_message(
            chat_id=target_id,
            text="🎉 Approved! Complete payment:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        await query.edit_message_text(query.message.text + "\n\n✅ Approved", parse_mode=ParseMode.HTML)
        return
    
    # Admin reject
    if data.startswith('reject_'):
        target_id = int(data.split('_')[1])
        context.user_data['reject_id'] = target_id
        
        await query.edit_message_reply_markup(reply_markup=None)
        await query.edit_message_text(query.message.text + "\n\n❌ Rejected", parse_mode=ParseMode.HTML)
        
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"Enter rejection reason for {target_id}:")
        return
    
    # Final approve
    if data.startswith('final_'):
        target_id = int(data.split('_')[1])
        
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE users SET status = 'completed' WHERE user_id = ?", (target_id,))
        conn.commit()
        conn.close()
        
        await query.edit_message_reply_markup(reply_markup=None)
        
        # Voice access granted
        await context.bot.send_voice(chat_id=target_id, voice=InputFile(generate_voice(VOICE_SCRIPTS['access_granted'])))
        
        await context.bot.send_message(
            chat_id=target_id,
            text=f"🔗 Telegram: {TELEGRAM_GROUP_LINK}\n📱 WhatsApp: {WHATSAPP_GROUP_LINK}"
        )
        
        await query.edit_message_text(query.message.caption + "\n\n✅ Links sent", parse_mode=ParseMode.HTML)
        return
    
    # Reject payment
    if data.startswith('rejectpay_'):
        target_id = int(data.split('_')[1])
        context.user_data['reject_id'] = target_id
        context.user_data['reject_payment'] = True
        
        await query.edit_message_reply_markup(reply_markup=None)
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"Enter payment rejection reason for {target_id}:")
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
        
        # Voice for email step
        await send_voice_message(update, user_id, 'step2_email')
        
        await update.message.reply_text(
            f"✅ Name: {text}\n\n📧 Enter email:",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Email
    if step == 'email_pending':
        if "@" not in text:
            await update.message.reply_text("❌ Invalid email!")
            return
        
        update_user(user_id, 'email', text)
        update_user(user_id, 'current_step', 'proof_pending')
        
        # Voice for proof step
        await send_voice_message(update, user_id, 'step3_proof')
        
        await update.message.reply_text(
            f"✅ Email: {text}\n\n📸 Upload proof:",
            parse_mode=ParseMode.HTML
        )
        return
    
    # WhatsApp
    if step == 'whatsapp_pending':
        clean = re.sub(r'[\s\-\(\)\.]', '', text)
        if not re.match(r'^\+\d{10,15}$', clean):
            await update.message.reply_text("❌ Invalid! Use: +923001234567")
            return
        
        update_user(user_id, 'whatsapp', clean)
        update_user(user_id, 'current_step', 'info_submitted')
        
        await update.message.reply_text("⏳ Submitted for review!")
        
        # Send to admin
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f'approve_{user_id}'),
                InlineKeyboardButton("❌ Reject", callback_data=f'reject_{user_id}')
            ]
        ]
        
        caption = f"🆕 Application\nUser: @{user_data[1]}\nID: {user_id}\nName: {user_data[2]}\nEmail: {user_data[3]}\nWhatsApp: {clean}\nType: {user_data[5]}"
        
        if user_data[6]:
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=user_data[6], caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await context.bot.send_message(chat_id=ADMIN_ID, text=caption, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # Rejection reason
    if 'reject_id' in context.user_data:
        target_id = context.user_data['reject_id']
        is_payment = context.user_data.get('reject_payment', False)
        
        # Voice rejection
        await context.bot.send_voice(chat_id=target_id, voice=InputFile(generate_voice(VOICE_SCRIPTS['rejected'])))
        
        await context.bot.send_message(chat_id=target_id, text=f"❌ Rejected\nReason: {text}")
        await update.message.reply_text(f"✅ User {target_id} rejected.")
        
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
        
        # Voice for WhatsApp step
        await send_voice_message(update, user_id, 'step4_whatsapp')
        
        await update.message.reply_text("✅ Proof received!\n\n📱 Enter WhatsApp (+923001234567):")
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
            # Voice duplicate warning
            await send_voice_message(update, user_id, 'duplicate_screenshot')
            
            await update.message.reply_text("🚫 DUPLICATE SCREENSHOT!")
            conn.close()
            return
        
        c.execute("INSERT INTO screenshots (file_hash, user_id, used_at) VALUES (?, ?, ?)", (hash_val, user_id, datetime.now()))
        c.execute("UPDATE users SET payment_file_id = ?, payment_hash = ?, current_step = 'payment_submitted', status = 'payment_verification' WHERE user_id = ?", (photo.file_id, hash_val, user_id))
        conn.commit()
        conn.close()
        
        # Voice payment received
        await send_voice_message(update, user_id, 'payment_received')
        
        await update.message.reply_text("⏳ Payment verifying...")
        
        # Send to admin
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve & Send Links", callback_data=f'final_{user_id}'),
                InlineKeyboardButton("❌ Reject Payment", callback_data=f'rejectpay_{user_id}')
            ]
        ]
        
        caption = f"💰 Payment Verify\nUser: @{user_data[1]}\nID: {user_id}\nName: {user_data[2]}\nMethod: {user_data[8]}"
        
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo.file_id, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))
        return

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("""
    ╔══════════════════════════════════════╗
    ║  🎙️ VOICE BOT ACTIVATED              ║
    ║  Premium Experience with Voice       ║
    ╚══════════════════════════════════════╝
    """)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
