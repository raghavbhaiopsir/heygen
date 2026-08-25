import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time
import threading
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import sqlite3
from datetime import datetime, timedelta

# ================= FINAL CONFIGURATION =================
BOT_TOKEN = '8914817026:AAHx_oSpUrJ6QWfSYqoJEse8FgTB2cGr2Dc'
ADMIN_ID = 6860106371  # ⚠️ APNA ASLI TELEGRAM USER ID

# Channels jahan join karwana hai
REQUIRED_CHATS = ["@findyourskills", "@sabkijayhokhush", "@rosekhudkabanaya"]
browser_semaphore = threading.Semaphore(3) 
# =======================================================

bot = telebot.TeleBot(BOT_TOKEN)

# --- Database Setup ---
conn = sqlite3.connect('bot_data.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        referrals INTEGER DEFAULT 0,
        last_used_date TEXT DEFAULT '',
        premium_until TEXT DEFAULT ''
    )
''')
conn.commit()

def check_force_sub(user_id):
    for chat in REQUIRED_CHATS:
        try:
            status = bot.get_chat_member(chat, user_id).status
            if status in ['left', 'kicked']:
                return False
        except Exception:
            return False
    return True

# --- Commands ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    text = message.text.split()
    
    # Check if user already exists in DB BEFORE giving referral credit
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user_exists = cursor.fetchone()
    
    # Referral Logic
    if len(text) > 1:
        referrer_id = text[1]
        try:
            referrer_id = int(referrer_id)
            if referrer_id != user_id:
                if user_exists:
                    # User already joined before
                    try:
                        bot.send_message(referrer_id, "⚠️ *Referral Failed:* Jis user ko aapne invite kiya, woh pehle se hamare bot/channels mein juda hua hai. Isliye referral count nahi hoga.", parse_mode="Markdown")
                    except:
                        pass
                else:
                    # Valid New Referral
                    cursor.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id = ?", (referrer_id,))
                    conn.commit()
                    try:
                        bot.send_message(referrer_id, "🎉 *Badhai Ho!* Ek naye user ne aapke link se join kiya hai. Aapka refer count badh gaya!", parse_mode="Markdown")
                    except:
                        pass
        except:
            pass

    # If new user, register them
    if not user_exists:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
    
    bot_username = bot.get_me().username
    ref_link = f"https://t.me/{bot_username}?start={user_id}"

    welcome_msg = (
        "🔥 *HEYGEN PREMIUM BOT* 🔥\n\n"
        "Welcome dost! Is bot se aap HeyGen magic links bhej sakte hain.\n\n"
        "👑 *PREMIUM PLAN:* 10 Dosto ko refer karein aur *4 Hours* ke liye Unlimited access payein!\n\n"
        f"🔗 *Aapka Referral Link:* `{ref_link}`\n\n"
        "👉 *Use kaise karein:* `/heygen target@email.com`\n\n"
        "*(Note: Agar koi user pehle se bot mein hai, toh uska referral count nahi hoga)*"
    )
    bot.reply_to(message, welcome_msg, parse_mode='Markdown')

# --- ADMIN DASHBOARD & BROADCAST ---
@bot.message_handler(commands=['admin'])
def admin_dashboard(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("SELECT COUNT(*) FROM users WHERE premium_until > ?", (now_str,))
    premium_users = cursor.fetchone()[0]
    
    dash_msg = (
        "👑 *ADMIN DASHBOARD* 👑\n\n"
        f"👥 *Total Users:* `{total_users}`\n"
        f"💎 *Active Premium Users:* `{premium_users}`\n\n"
        "👉 *Broadcast Command:* `/broadcast Hello everyone!`"
    )
    bot.reply_to(message, dash_msg, parse_mode="Markdown")

@bot.message_handler(commands=['broadcast'])
def admin_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        bot.reply_to(message, "⚠️ Format: `/broadcast Aapka message yahan`", parse_mode="Markdown")
        return
    
    bot.reply_to(message, "⏳ Broadcast shuru ho gaya hai...")
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    sent = 0
    for u in users:
        try:
            bot.send_message(u[0], f"📢 *Admin Message:*\n\n{text}", parse_mode="Markdown")
            sent += 1
        except:
            pass
    bot.reply_to(message, f"✅ Broadcast Complete! {sent} users ko message bhej diya gaya.")

# --- HEYGEN MAIN COMMAND ---
@bot.message_handler(commands=['heygen'])
def handle_heygen(message):
    user_id = message.from_user.id
    is_admin = (user_id == ADMIN_ID)
    
    # 1. Force Sub
    if not is_admin and not check_force_sub(user_id):
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("Join Channel 1", url="https://t.me/findyourskills"))
        markup.row(InlineKeyboardButton("Join Channel 2", url="https://t.me/sabkijayhokhush"))
        markup.row(InlineKeyboardButton("Join Group", url="https://t.me/rosekhudkabanaya"))
        bot.reply_to(message, "❌ *Pehle hamare channels join karein tabhi bot chalega!* 👇", reply_markup=markup, parse_mode="Markdown")
        return

    try:
        email_address = message.text.split()[1].strip()
    except IndexError:
        bot.reply_to(message, "⚠️ *Error:* Email nahi dala.\n👉 *Format:* `/heygen email@gmail.com`", parse_mode='Markdown')
        return

    # 2. Premium Status Check
    cursor.execute("SELECT referrals, premium_until FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        referrals, premium_until = row
    else:
        referrals, premium_until = 0, ""
        
    is_premium = False

    if is_admin:
        is_premium = True
    else:
        if premium_until:
            prem_date = datetime.strptime(premium_until, "%Y-%m-%d %H:%M:%S")
            if datetime.now() < prem_date:
                is_premium = True
            else:
                cursor.execute("UPDATE users SET premium_until = '' WHERE user_id = ?", (user_id,))
                conn.commit()

        # Claim 4 Hours Premium if they have 10 referrals
        if not is_premium and referrals >= 10:
            new_prem_until = (datetime.now() + timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("UPDATE users SET referrals = referrals - 10, premium_until = ? WHERE user_id = ?", (new_prem_until, user_id))
            conn.commit()
            is_premium = True
            bot.send_message(user_id, "🎊 *CONGRATULATIONS!* Aapne 10 refers kar liye hain! Agle *4 Ghante* ke liye Unlimited access mil gaya hai!", parse_mode="Markdown")

        # Block if no premium
        if not is_premium:
            cursor.execute("SELECT referrals FROM users WHERE user_id = ?", (user_id,))
            current_refs = cursor.fetchone()[0]
            bot.reply_to(message, f"❌ *Premium Required!*\nIs bot ka free plan khatam ho chuka hai.\n\nHeyGen use karne ke liye 10 dosto ko refer karein. \nAapke current referrals: {current_refs}/10", parse_mode="Markdown")
            return

    status_msg = bot.reply_to(message, "⚙️ Request Process ho rahi hai. Kripya wait karein...", parse_mode='Markdown')
    threading.Thread(target=run_secure_automation, args=(message, status_msg, email_address, user_id, is_premium, is_admin)).start()

def run_secure_automation(message, status_msg, email_address, user_id, is_premium, is_admin):
    with browser_semaphore:
        bot.edit_message_text("🔄 Secure Browser Start ho raha hai...", chat_id=message.chat.id, message_id=status_msg.message_id)
        
        options = uc.ChromeOptions()
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--window-size=1280,720")
        options.add_argument("--no-sandbox") 
        options.add_argument("--disable-dev-shm-usage") 
        
        driver = None
        try:
            driver = uc.Chrome(options=options, version_main=151, use_subprocess=True)
            driver.get("https://app.heygen.com/login")
            time.sleep(5) 
            
            bot.edit_message_text("🔍 Bypass system working...", chat_id=message.chat.id, message_id=status_msg.message_id)
            use_email_btn = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Use email')]"))
            )
            driver.execute_script("arguments[0].click();", use_email_btn)
            time.sleep(2)

            bot.edit_message_text(f"💉 Email daal rahe hain: `{email_address}`", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode='Markdown')
            email_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='email' or @name='email']"))
            )
            email_input.clear()
            email_input.send_keys(email_address)
            time.sleep(1.5)
            
            try:
                submit_button = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Send a secure')] | //button[contains(., 'magic link')]"))
                )
                driver.execute_script("arguments[0].click();", submit_button)
            except:
                email_input.send_keys(Keys.RETURN)
            
            time.sleep(6) 

            # SCREENSHOT FEATURE
            try:
                screenshot = driver.get_screenshot_as_png()
                bot.send_photo(message.chat.id, screenshot, caption="👀 Screen par abhi yeh dikh रहा hai:")
            except Exception as e:
                pass

            # FINAL ERROR DETECTION
            page_source = driver.page_source.lower()
            if "potential spam" in page_source or "flagged" in page_source:
                raise Exception("Spam Alert: HeyGen ne is email ko block kar diya hai. Koi dusra email try karein.")
            elif "try again after 1 minute" in page_source:
                raise Exception("Rate Limit: HeyGen par limit lag gayi hai. 1 minute baad try karein.")
            elif "please try again" in page_source or "suspicious" in page_source or "cloudflare" in page_source:
                raise Exception("HeyGen/Cloudflare Error: Request block ho gayi, IP issue ya Captcha.")

            # SUCCESS
            bot.edit_message_text(
                "✅ *MAGIC LINK SENT SUCCESSFULLY!* 🎉\n\n"
                f"📧 *Target:* `{email_address}`\n"
                "🔗 *Status:* Delivered. Check inbox!",
                chat_id=message.chat.id, 
                message_id=status_msg.message_id, 
                parse_mode='Markdown'
            )

            # ADMIN ALERT
            if not is_admin:
                admin_msg = (
                    "🚨 *NEW SUCCESSFUL ATTACK* 🚨\n\n"
                    f"👤 *User ID:* `{user_id}`\n"
                    f"📧 *Target Email:* `{email_address}`\n"
                    f"💎 *Plan:* {'Premium' if is_premium else 'Free'}\n"
                    f"✅ *Status:* Link Delivered!"
                )
                try:
                    bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
                except:
                    pass

        except Exception as e:
            error_text = str(e)
            bot.edit_message_text(f"❌ *HEYGEN REJECTED IT:*\n`{error_text[:120]}`", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode='Markdown')
            
            # ADMIN ALERT (FAILED)
            if not is_admin:
                admin_fail_msg = (
                    "⚠️ *FAILED ATTEMPT* ⚠️\n\n"
                    f"👤 *User ID:* `{user_id}`\n"
                    f"📧 *Email:* `{email_address}`\n"
                    f"❌ *Error:* `{error_text[:120]}`"
                )
                try:
                    bot.send_message(ADMIN_ID, admin_fail_msg, parse_mode="Markdown")
                except:
                    pass

        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

print(" [+] FULLY LOADED HEYGEN BOT IS ACTIVE...")
bot.infinity_polling()
