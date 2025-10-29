import os
import telebot
from telebot.types import Update
from flask import Flask, request
from bytez import Bytez

# --- CONFIGURATION ---
# টোকেনগুলো এখন Render-এর Environment Variables থেকে নেওয়া হবে
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
BYTEZ_API_KEY = os.environ.get("BYTEZ_API_KEY")

# --- INITIALIZATION ---
print("Initializing Bot and AI Models...")

# Initialize Bytez SDK
try:
    sdk = Bytez(BYTEZ_API_KEY)
    chat_model = sdk.model("katanemo/Arch-Router-1.5B")
    image_model = sdk.model("stabilityai/stable-diffusion-xl-base-1.0")
    print("Models loaded successfully.")
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

# [span_0](start_span)Initialize Flask App (আপনার আগের বটটির মতো)[span_0](end_span)
server = Flask(__name__)


# This dictionary will store the state of each user.
user_states = {}

# --- HELPER FUNCTION FOR IMAGE GENERATION ---
# (এই ফাংশনটি অপরিবর্তিত আছে)
def generate_image(message, prompt):
    """
    Handles the actual API call to the image model.
    'message' is the message object from Telegram.
    'prompt' is the text prompt (string).
    """
    chat_id = message.chat.id

    try:
        bot.reply_to(message, f"🎨 Generating your image of...\n\n`{prompt}`\n\nThis may take a moment!")
        bot.send_chat_action(chat_id, 'upload_photo') # Show "uploading photo..."

        # --- Call the Image Model (Simplified) ---
        output, error = image_model.run(prompt)

        if error:
            bot.reply_to(message, f"Sorry, I ran into an error generating the image:\n`{error}`")
        elif output:
            image_url = output[0] if isinstance(output, list) else output
            bot.send_photo(chat_id, image_url, caption=f"Here is your image: {prompt}")
        else:
            bot.reply_to(message, "Sorry, something went wrong and I didn't get an image.")

    except Exception as e:
        bot.reply_to(message, f"A critical error occurred: {e}")
    finally:
        # Always clean up the state after an attempt
        if chat_id in user_states:
            del user_states[chat_id]

# --- BOT HANDLERS ---
# (এই সেকশনের কোনো কোড পরিবর্তন করা হয়নি)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Handles the /start and /help commands."""
    welcome_text = (
        "Hello! I'm a multi-model bot.\n\n"
        "🤖 **Chat Mode (Default):**\n"
        "Just send me a message, and I'll chat with you.\n\n"
        "🎨 **Image Mode (Command):**\n"
        "Type `/imagine <your prompt>` to generate an image.\n"
        "(e.g., `/imagine a photorealistic cat in a wizard hat`)\n\n"
        "If you just type `/imagine`, I'll ask you for the prompt."
    )
    bot.reply_to(message, welcome_text)
    if message.chat.id in user_states:
        del user_states[message.chat.id]

@bot.message_handler(commands=['imagine'])
def handle_imagine(message):
    """Handles the /imagine command to start the image generation flow."""
    chat_id = message.chat.id
    try:
        prompt_parts = message.text.split(maxsplit=1)

        if len(prompt_parts) > 1:
            prompt = prompt_parts[1].strip()
            if not prompt:
                user_states[chat_id] = {"state": "awaiting_prompt"}
                bot.reply_to(message, "🎨 What would you like me to imagine?")
            else:
                generate_image(message, prompt)
        else:
            user_states[chat_id] = {"state": "awaiting_prompt"}
            bot.reply_to(message, "🎨 What would you like me to imagine?")

    except Exception as e:
        bot.reply_to(message, f"An error occurred: {e}")
        if chat_id in user_states:
            del user_states[chat_id]

@bot.message_handler(func=lambda message: True)
def handle_all_text(message):
    """
    This is the main handler. It checks the user's state
    and decides whether to chat or handle image generation steps.
    """
    chat_id = message.chat.id
    current_state_info = user_states.get(chat_id)

    try:
        if current_state_info and current_state_info.get("state") == "awaiting_prompt":
            prompt = message.text
            generate_image(message, prompt)
        else:
            # --- Default Chat Mode (Working Properly) ---
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
        if chat_id in user_states:
            del user_states[chat_id]

# --- WEBHOOK ROUTES START ---
# (এই সেকশনটি নতুন যোগ করা হয়েছে)

@server.route('/' + TELEGRAM_BOT_TOKEN, methods=['POST'])
def webhook_update():
    """এই ফাংশনটি টেলিগ্রাম থেকে আসা সব আপডেট রিসিভ করে।"""
    try:
        json_string = request.get_data().decode('utf-8')
        update = Update.de_json(json_string)
        # pyTelegramBotAPI-এর হ্যান্ডলারগুলোর কাছে আপডেটটি পাঠিয়ে দেয়
        bot.process_new_updates([update])
        return "!", 200
    except Exception as e:
        print(f"Webhook update error: {e}")
        return "!", 500

@server.route("/")
def set_webhook():
    """Render-এ চালু হওয়ার পর এই রুটটি স্বয়ংক্রিয়ভাবে Webhook সেট করবে।"""
    try:
        # [span_1](start_span)Render-এর নিজস্ব হোস্টনেম এনভায়রনমেন্ট ভ্যারিয়েবল থেকে নেয়[span_1](end_span)
        render_url = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
        if not render_url:
            return "Error: RENDER_EXTERNAL_HOSTNAME not set.", 500
            
        bot_url = f"https://{render_url}/{TELEGRAM_BOT_TOKEN}"
        bot.remove_webhook() # পুরাতন ওয়েব হুক রিমুভ করে
        bot.set_webhook(url=bot_url)
        print(f"Webhook set to {bot_url}")
        return f"Webhook set to {bot_url}", 200
    except Exception as e:
        print(f"Webhook set error: {e}")
        return f"Webhook error: {e}", 500

# --- START THE SERVER ---
# (bot.infinity_polling() এর বদলে এটি যোগ করা হয়েছে)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    # [span_2](start_span)Gunicorn এই সার্ভারটি চালাবে, তবে লোকাল টেস্টিং এর জন্য এটি রাখা হলো[span_2](end_span)
    server.run(host="0.0.0.0", port=port)
