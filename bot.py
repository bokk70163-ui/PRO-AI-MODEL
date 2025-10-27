import urllib.request
import os
import telebot
from bytez import Bytez
from flask import Flask, request

# --- CONFIGURATION ---
# As you requested, the API keys are here.
# Replace these placeholder strings with your actual keys.
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"
user_data = {}

BYTEZ_API_KEY = os.environ.get("BYTEZ_API_KEY")
# --- Flask App ---
server = Flask(__name__)

print("Initializing Bot and AI Chat Model...")

# Initialize Bytez SDK
try:
    sdk = Bytez(BYTEZ_API_KEY)
    
    # Initialize the chat model
    chat_model = sdk.model("katanemo/Arch-Router-1.5B")
    
    print("Chat model loaded successfully.")
except Exception as e:
    print(f"Error initializing Bytez SDK or model: {e}")
    print("Please check your BYTEZ_API_KEY.")
    exit()

# Initialize Telegram Bot
try:
    bot = telebot.TeleBot(BOT_TOKEN)
    # Test bot connection
    bot_info = bot.get_me()
    print(f"Bot '{bot_info.first_name}' (username: @{bot_info.username}) is connecting...")
except Exception as e:
    print(f"Error connecting to Telegram. Is your TELEGRAM_BOT_TOKEN correct? Error: {e}")
    exit()

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
    This handler listens for any text message and replies using the chat model.
    """
    chat_id = message.chat.id
    
    try:
        # --- Default Chat Mode ---
        bot.send_chat_action(chat_id, 'typing') # Show "typing..."
        
        chat_input = [
            {"role": "user", "content": message.text}
        ]
        
        output, error = chat_model.run(chat_input)
        
        if error:
            bot.reply_to(message, f"Sorry, I ran into a chat error:\n`{error}`")
        elif output and output.get("content"):
            bot.reply_to(message, output["content"])
        else:
            bot.reply_to(message, "Sorry, I'm not sure how to respond to that.")

    except Exception as e:
        bot.reply_to(message, f"A critical error occurred: {e}")
        
        # --- Webhook Routes ---
@server.route('/' + BOT_TOKEN, methods=['POST'])
def webhook_update():
    update = request.get_json()
    if "message" in update:
        handle_command(update["message"])
    elif "callback_query" in update:
        handle_callback(update["callback_query"])
    return "ok", 200

@server.route("/")
def set_webhook():
    import os
    bot_url = "https://{}/{}".format(os.environ.get("RENDER_EXTERNAL_HOSTNAME"), BOT_TOKEN)
    req = urllib.request.Request(API_URL + "setWebhook?url=" + bot_url)
    try:
        urllib.request.urlopen(req)
        return "Webhook set!", 200
    except Exception as e:
        return f"Webhook error: {e}", 500

if __name__ == "__main__":
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
