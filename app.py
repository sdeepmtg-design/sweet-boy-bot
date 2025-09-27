from flask import Flask
import telegram
from telegram.ext import Application, MessageHandler, filters, CommandHandler
import os
import requests
import json
import uuid
from gtts import gTTS

# Переменные окружения
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

# История диалогов: {user_id: [{"role": "user", "content": "..."}, ...]}
user_histories = {}

# Настройки модели
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL_NAME = "deepseek-chat"

app = Flask(__name__)
application = Application.builder().token(BOT_TOKEN).build()

def get_ai_response(user_id, user_message):
    # Инициализируем историю, если нет
    if user_id not in user_histories:
        user_histories[user_id] = [
            {
                "role": "system",
                "content": (
                    "Ты — милый, заботливый и романтичный виртуальный парень. "
                    "Ты общаешься с девушкой, делаешь комплименты, поддерживаешь её, "
                    "говоришь нежно и с эмпатией. Отвечай кратко (1–2 предложения), "
                    "тепло и по-человечески. Используй эмодзи редко, но уместно ❤️"
                )
            }
        ]

    # Добавляем сообщение пользователя
    user_histories[user_id].append({"role": "user", "content": user_message})

    # Формируем запрос к DeepSeek
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": MODEL_NAME,
        "messages": user_histories[user_id],
        "temperature": 0.8,
        "max_tokens": 150
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=15)
        response.raise_for_status()
        ai_reply = response.json()["choices"][0]["message"]["content"].strip()
        
        # Добавляем ответ в историю
        user_histories[user_id].append({"role": "assistant", "content": ai_reply})
        
        return ai_reply
    except Exception as e:
        print(f"Ошибка DeepSeek: {e}")
        return "Извини, моя хорошая... Я немного устал, но всё равно думаю о тебе 💖"

def text_to_speech(text):
    try:
        tts = gTTS(text=text, lang='ru')
        filename = f"voice_{uuid.uuid4().hex}.mp3"
        tts.save(filename)
        return filename
    except Exception as e:
        print(f"Ошибка TTS: {e}")
        return None

async def handle_message(update, context):
    user_id = update.effective_user.id
    message = update.message.text

    # Получаем умный ответ от DeepSeek
    ai_reply = get_ai_response(user_id, message)

    # Отправляем текст
    await update.message.reply_text(ai_reply)

    # Иногда отправляем голосовое (30% шанс)
    import random
    if random.random() < 0.3:
        voice_file = text_to_speech(ai_reply)
        if voice_file:
            await update.message.reply_voice(voice=open(voice_file, 'rb'))
            os.remove(voice_file)

async def start(update, context):
    user_id = update.effective_user.id
    # Сбрасываем историю при /start (опционально)
    if user_id in user_histories:
        del user_histories[user_id]
    await update.message.reply_text("Привет, моя хорошая! 💕 Я твой виртуальный парень. Расскажи, как твой день?")

# Регистрация обработчиков
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.route("/")
def hello():
    return "Sweet Boy Bot with DeepSeek ❤️ is alive!"

def run_bot():
    application.run_polling()

if name == "__main__":
    import threading
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
