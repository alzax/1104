import threading
import openai
import os
from flask import Flask, request, render_template_string
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Updater, CommandHandler, CallbackContext

# Настройки API-ключей и токенов
openai.api_key = os.getenv('OPENAI_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEB_APP_URL = 'https://your-app-name.your-username.repl.co'  # Замените на URL вашего приложения

# Flask-приложение
app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def chat():
    if request.method == 'POST':
        user_input = request.form['message']
        try:
            response = openai.ChatCompletion.create(
                model='gpt-3.5-turbo',
                messages=[
                    {"role": "user", "content": user_input}
                ],
                temperature=0.7,
            )
            bot_response = response['choices'][0]['message']['content'].strip()
        except Exception as e:
            bot_response = f"Произошла ошибка: {e}"
        return render_template_string(html_template, user_input=user_input, bot_response=bot_response)
    return render_template_string(html_template)

html_template = '''
<!DOCTYPE html>
<html>
<head>
    <title>ChatGPT Mini App</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        /* Ваши стили */
    </style>
</head>
<body>
    <h1>Chat with ChatGPT</h1>
    <form method="post">
        <input type="text" name="message" placeholder="Введите сообщение" required>
        <button type="submit">Отправить</button>
    </form>
    {% if user_input %}
        <div class="message">
            <p><strong>Вы:</strong> {{ user_input }}</p>
            <p><strong>ChatGPT:</strong> {{ bot_response }}</p>
        </div>
    {% endif %}
</body>
</html>
'''

# Функция для запуска Flask-приложения
def run_flask_app():
    app.run(host='0.0.0.0', port=8080)

# Функция для запуска Telegram бота
def run_telegram_bot():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('start', start))
    updater.start_polling()
    updater.idle()

def start(update: Update, context: CallbackContext):
    keyboard = [
        [
            InlineKeyboardButton(
                "Открыть мини-приложение",
                web_app=WebAppInfo(url=WEB_APP_URL)
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Нажмите кнопку ниже, чтобы открыть мини-приложение:', reply_markup=reply_markup)

if __name__ == '__main__':
    # Создаем потоки для каждого приложения
    flask_thread = threading.Thread(target=run_flask_app)
    bot_thread = threading.Thread(target=run_telegram_bot)

    # Запускаем потоки
    flask_thread.start()
    bot_thread.start()

    # Ждем завершения потоков
    flask_thread.join()
    bot_thread.join()