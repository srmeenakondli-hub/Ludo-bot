import telebot
from telebot import types
import re
import json
import os
import time
import threading
from flask import Flask

app = Flask('')

@app.route('/')
def home():
    return "Ajay Ludo Bot is Alive 24/7!"

def run_web_server():
    app.run(host='0.0.0.0', port=8080)

API_TOKEN = '8721200541:AAH0TOK0NMQ6w9DNN6hdQHi13hh_dLcsvX0'
bot = telebot.TeleBot(API_TOKEN)

BALANCE_FILE = "ludo_balances.json"
MAPPING_FILE = "username_mapping.json"
QR_FILE = "qr_data.json"

def load_data(file_name):
    if os.path.exists(file_name):
        with open(file_name, 'r') as f: 
            try: return json.load(f)
            except: return {}
    return {}

def load_balances(file_name):
    if os.path.exists(file_name):
        with open(file_name, 'r') as f:
            try:
                data = json.load(f)
                return {str(k): float(v) for k, v in data.items()}
            except:
                return {}
    return {}

def save_data(file_name, data):
    with open(file_name, 'w') as f: json.dump(data, f, indent=4)

user_balances = load_balances(BALANCE_FILE)
username_to_id = load_data(MAPPING_FILE)
qr_data = load_data(QR_FILE)

def auto_delete_msg(chat_id, message_id):
    def delete():
        time.sleep(60)
        try: bot.delete_message(chat_id, message_id)
        except: pass
    threading.Thread(target=delete).start()

def send_smart_reply(message, text, reply_markup=None):
    try:
        msg = bot.reply_to(message, text, reply_markup=reply_markup, parse_mode="Markdown")
        auto_delete_msg(message.chat.id, msg.message_id)
        return msg
    except Exception as e:
        print(f"Reply Error: {e}")

def is_group_admin(chat_id, user_id):
    try:
        admins = bot.get_chat_administrators(chat_id)
        return any(admin.user.id == user_id for admin in admins)
    except:
        return False

def parse_amount(amount_str):
    amount_str = amount_str.lower().replace('r', '').replace('s', '').strip()
    try:
        if 'k' in amount_str:
            return float(amount_str.replace('k', '')) * 1000
        return float(amount_str)
    except ValueError:
        return None

def send_pm_receipt(user_id, text):
    try: bot.send_message(int(user_id), text, parse_mode="Markdown")
    except: pass

def get_live_balance_list(chat_id):
    active_players = []
    for uid_str, bal in user_balances.items():
        if bal > 0:
            try:
                member = bot.get_chat_member(chat_id, int(uid_str))
                name = member.user.first_name
            except:
                name = f"User_{uid_str}"
            active_players.append((name, bal))
            
    if not active_players:
        return "📊 **LIVE BALANCE LIST:**\n\nकोई भी खिलाड़ी लिस्ट में नहीं है।"
        
    active_players.sort(key=lambda x: x.lower())
    
    list_text = "📊 **LIVE BALANCE LIST (A to Z)**\n"
    list_text += "━━━━━━━━━━━━━━━━━━━━━\n"
    for i, (name, bal) in enumerate(active_players, 1):
        list_text += f"{i}. 👤 {name} : {bal:.2f} रुपये\n"
    list_text += "━━━━━━━━━━━━━━━━━━━━━"
    return list_text

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    username = message.from_user.username
    if user_id not in user_balances: user_balances[user_id] = 0.0
    if username: username_to_id[username.lower()] = user_id
    save_data(BALANCE_FILE, user_balances)
    save_data(MAPPING_FILE, username_to_id)
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("Check Your Stats 📊", callback_data="check_balance")
    markup.add(btn)
    bot.reply_to(message, "✅ आप अजय लूडो ऑटोमेशन बोट से जुड़ चुके हैं।", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_balance")
def callback_inline(call):
    uid = str(call.from_user.id)
    bal = user_balances.get(uid, 0.0)
    bot.answer_callback_query(call.id, text=f"👤 आपका बैलेंस: {bal} रुपये", show_alert=True)

@bot.message_handler(func=lambda message: True, content_types=['text', 'photo'])
def handle_all_messages(message):
    chat_id = message.chat.id
    user_id = str(message.from_user.id)
    username = message.from_user.username
    if username: username_to_id[username.lower()] = user_id
    if user_id not in user_balances: user_balances[user_id] = 0.0
    save_data(MAPPING_FILE, username_to_id)

    if message.text and any(word in message.text.lower() for word in ['balance', 'बैलेंस', '/balance']):
        bal = user_balances.get(user_id, 0.0)
        reply = f"👤 **{message.from_user.first_name}'s INFO**\n━━━━━━━━━━━━━━━━━━\n💵 **Balance** : {bal:.2f} रुपये\n━━━━━━━━━━━━━━━━━━"
        send_smart_reply(message, reply)
        return

    if message.text and message.text.lower() in ['qr', 'क्यूआर', 'qrcode']:
        if "photo_id" in qr_data:
            msg = bot.send_photo(chat_id, qr_data["photo_id"], caption=f"ℹ️ **QR CODE:** {qr_data.get('name', 'Admin Pay')}\n*(यह मैसेज 1 मिनट में डिलीट हो जाएगा)*")
            auto_delete_msg(chat_id, msg.message_id)
        else:
            send_smart_reply(message, "❌ कोई क्यूआर कोड सेट नहीं है।")
        return

    if not is_group_admin(chat_id, message.from_user.id):
        return

    if message.photo and message.caption and message.caption.lower().startswith('qr set'):
        name = message.caption[6:].strip()
        photo_id = message.photo[-1].file_id
        global qr_data
        qr_data = {"photo_id": photo_id, "name": name}
        save_data(QR_FILE, qr_data)
        send_smart_reply(message, f"✅ क्यूआर कोड `{name}` के लिए सफलतापूर्वक सेट हो गया है!")
        return

    if message.text:
        text_lower = message.text.lower()
        args = message.text.split()

        if text_lower.startswith('win'):
            if not message.reply_to_message or len(args) < 3:
                send_smart_reply(message, "⚠️ सही फॉर्मेट: टेबल पर रिप्लाई करके लिखें `win @winner 10k`")
                return
            winner_user = args.replace('@', '').lower()
            bet_str = args.lower()
            amount = parse_amount(bet_str)
            if not amount or winner_user not in username_to_id:
                send_smart_reply(message, "⚠️ रकम गलत है या खिलाड़ी रजिस्टर्ड नहीं है।")
                return
            table_text = message.reply_to_message.text or ""
            all_users = [u.replace('@', '').lower() for u in re.findall(r'@\w+', table_text)]
            loser_user = None
            for u in all_users:
                if u != winner_user: loser_user = u; break
            if not loser_user or loser_user not in username_to_id:
                send_smart_reply(message, "❌ बोट हारने वाले का नाम नहीं ढूंढ पाया।")
                return
            win_id, los_id = username_to_id[winner_user], username_to_id[loser_user]
            commission = amount * 0.05
            net_profit = amount - commission
            user_balances[los_id] -= amount
            if user_balances[los_id] < 0: user_balances[los_id] = 0.0
            user_balances[win_id] += net_profit
            save_data(BALANCE_FILE, user_balances)
            send_smart_reply(message, f"🏆 **MATCH UPDATED** 🏆\n🥇 **Winner:** @{winner_user} (+{net_profit:.2f})\n🥈 **Loser:** @{loser_user} (-{amount})\n💼 **Comm (5%):** {commission:.2f}\n\n" + get_live_balance_list(chat_id))
            send_pm_receipt(win_id, f"🎉 **WIN ALERT**\n🤝 Table against: @{loser_user}\n💰 Bet: {amount}\n📈 Net Profit: {net_profit:.2f}\n💵 Balance: {user_balances[win_id]:.2f}")
            send_pm_receipt(los_id, f"💔 **LOSS ALERT**\n🤝 Table against: @{winner_user}\n📉 Deducted: -{amount}\n💵 Balance: {user_balances[los_id]:.2f}")
            return

        is_add = text_lower.startswith(('add', '/add'))
        is_cut = text_lower.startswith(('cut', '/cut', 'minus'))
        if is_add or is_cut:
            target_id = None
            amt_str = ""
            if message.reply_to_message and len(args) >= 2:
                target_id = str(message.reply_to_message.from_user.id)
                amt_str = args
            elif len(args) >= 3 and args.startswith('@'):
                u_name = args.replace('@', '').lower()
                target_id = username_to_id.get(u_name)
                amt_str = args
            amount = parse_amount(amt_str) if amt_str else None
            if not target_id or not amount:
                send_smart_reply(message, "⚠️ सही फॉर्मेट: `add 2k` (रिप्लाई करके) या `add @username 500` ")
                return
            if is_add:
                user_balances[target_id] += amount
                action_type = "💰 DEPOSIT (ADD)"
                symbol = "+"
            else:
                user_balances[target_id] -= amount
                if user_balances[target_id] < 0: user_balances[target_id] = 0.0
                action_type = "📉 WITHDRAW (CUT)"
                symbol = "-"
            save_data(BALANCE_FILE, user_balances)
            try: t_name = bot.get_chat_member(chat_id, int(target_id)).user.first_name
            except: t_name = f"User_{target_id}"
            send_smart_reply(message, f"✅ **BALANCE UPDATED**\n👤 Player: {t_name}\n⚙️ Action: {action_type}\n💵 Amount: {symbol}{amount} रुपये\n\n" + get_live_balance_list(chat_id))
            send_pm_receipt(target_id, f"ℹ️ **BALANCE ALERT ({action_type})**\n━━━━━━━━━━━━━━━━━━\n💰 Amount: {symbol}{amount} रुपये\n💵 Total Balance: {user_balances[target_id]:.2f} रुपये\n━━━━━━━━━━━━━━━━━━")

if __name__ == '__main__':
    t = threading.Thread(target=run_web_server)
    t.start()
    bot.infinity_polling()
              
