import os
import telebot
from telebot.types import Update
from flask import Flask, request
from bytez import Bytez

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
BYTEZ_API_KEY = os.environ.get("BYTEZ_API_KEY")

# --- INITIALIZATION ---
print("Initializing Bot and AI Models...")

# Initialize Bytez SDK
try:
    sdk = Bytez(BYTEZ_API_KEY)
    # শুধুমাত্র চ্যাট মডেলটি লোড করা হচ্ছে
    chat_model = sdk.model("katanemo/Arch-Router-1.5B")
    print("Chat model loaded successfully.")
except Exception as e:
    print(f"Error initializing Bytez SDK or models: {e}")
    exit()

# Initialize Telegram Bot
try:
    bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
    bot_info = bot.get_me()
    print(f"Bot '{bot_info.first_name}' (username: @{bot_info.username}) is connecting...")
except Exception as e:
    print(f"Error connecting to Telegram: {e}")
    exit()

# Initialize Flask App
server = Flask(__name__)

# --- BOT HANDLERS ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Handles the /start and /help commands."""
    welcome_text = (
        "Hello! I'm a chat bot.\n\n"
        "Just send me a message, and I'll chat with you."
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(func=lambda message: True)
def handle_all_text(message):
    """
    This handler processes all incoming text messages for chatting.
    """
    chat_id = message.chat.id

    try:
        # --- Default Chat Mode ---
        bot.send_chat_action(chat_id, 'typing') 
        chat_input = [{"role": "user", "content": message.text}]
        
        output, error = chat_model.run(chat_input)

        if error:
            bot.reply_to(message, f"Sorry, I ran into a chat error:\n`{error}`")
        elif output and output.get("content"):
            bot.reply_to(message, output["content"])
        else:
            bot.reply_to(message, "Sorry, I'm not sure how to respond to that.")

    except Exception as e:
        bot.reply_to(message, f"A critical error occurred: {e}")

# --- WEBHOOK ROUTES START ---
# (এই অংশটি অপরিবর্তিত আছে)

@server.route('/' + TELEGRAM_BOT_TOKEN, methods=['POST'])
def webhook_update():
    """Handles all updates from Telegram."""
    try:
        json_string = request.get_data().decode('utf-8')
        update = Update.de_json(json_string)
        bot.process_new_updates([update])
        return "!", 200
    except Exception as e:
        print(f"Webhook update error: {e}")
        return "!", 500

@server.route("/")
def set_webhook():
    """Sets the webhook automatically when the service starts."""
    try:
        render_url = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
        if not render_url:
            return "Error: RENDER_EXTERNAL_HOSTNAME not set.", 500
            
        bot_url = f"https://{render_url}/{TELEGRAM_BOT_TOKEN}"
        bot.remove_webhook() 
        bot.set_webhook(url=bot_url)
        print(f"Webhook set to {bot_url}")
        return f"Webhook set to {bot_url}", 200
    except Exception as e:
        print(f"Webhook set error: {e}")
        return f"Webhook error: {e}", 500

# --- START THE SERVER ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    server.run(host="0.0.0.0", port=port)
