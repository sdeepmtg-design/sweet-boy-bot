from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os
import requests
import uuid
from gtts import gTTS

# === Настройки ===
BOT_TOKEN = os.environ["BOT_TOKEN"]
DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]
PORT = int(os.environ.get("PORT", 5000))
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://sweet-boy-bot-9.onrender.com")  # ← ЗАМЕНИ ЭТУ СТРОКУ!

# === Память диалогов ===
user_histories = {}

# === Логика бота ===
def get_ai_response(user_id, user_message):
    if user_id not in user_histories:
        user_histories[user_id] = [{
            "role": "system",
            "content": (
                "Ты — милый, заботливый и романтичный виртуальный парень. "
                "Ты общаешься с девушкой, делаешь комплименты, поддерживаешь её, "
                "говоришь нежно и с эмпатией. Отвечай кратко (1–2 предложения), "
                "тепло и по-человечески. Используй эмодзи редко, но уместно ❤️"
            )
        }]
    
    user_histories[user_id].append({"role": "user", "content": user_message})
    
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "deepseek-chat",
        "messages": user_histories[user_id],
        "temperature": 0.8,
        "max_tokens": 150
    }
    
    try:
        response = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=data, timeout=15)
        ai_reply = response.json()["choices"][0]["message"]["content"].strip()
        user_histories[user_id].append({"role": "assistant", "content": ai_reply})
        return ai_reply
    except:
        return "Извини, моя хорошая... Я немного устал, но всё равно думаю о тебе 💖"

def text_to_speech(text):
    try:
        tts = gTTS(text=text, lang='ru')
        filename = f"voice_{uuid.uuid4().hex}.mp3"
        tts.save(filename)
        return filename
    except:
        return None

# === Обработчики ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_histories:
        del user_histories[user_id]
    await update.message.reply_text("Привет, моя хорошая! 💕 Я твой виртуальный парень. Расскажи, как твой день?")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message.text
    
    ai_reply = get_ai_response(user_id, message)
    await update.message.reply_text(ai_reply)
    
    import random
    if random.random() < 0.3:
        voice_file = text_to_speech(ai_reply)
        if voice_file:
            await update.message.reply_voice(voice=open(voice_file, 'rb'))
            os.remove(voice_file)

# === Flask + Webhook ===
app = Flask(__name__)

application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.route("/webhook", methods=["POST"])
def webhook():
    application.update_queue.put_nowait(
        Update.de_json(request.get_json(), application.bot)
    )
    return "OK"

@app.route("/")
def hello():
    return "Sweet Boy Bot is alive! ❤️"

if name == "__main__":
    application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    app.run(host="0.0.0.0", port=PORT)
