import os
import openai
from flask import Flask, request, render_template, redirect, url_for, session
from flask_session import Session
import random

app = Flask(__name__)

# Конфигурация сессий
app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey')  # Задайте свой секретный ключ
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
Session(app)

# Установка API-ключа OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')  # Ваш OpenAI API ключ

@app.route('/', methods=['GET', 'POST'])
def index():
    # Получение или инициализация данных пользователя в сессии
    if 'user_data' not in session:
        session['user_data'] = {
            'step': 1,
            'language': '',
            'topic': '',
            'words': [],
            'current_word_index': 0,
            'correct_answers': []
        }

    user = session['user_data']
    step = user['step']

    if request.method == 'POST':
        if 'reset' in request.form:
            # Сброс данных пользователя
            session.pop('user_data', None)
            return redirect(url_for('index'))
        elif 'back' in request.form:
            # Шаг назад
            if step > 1:
                user['step'] -= 1
                session['user_data'] = user
            return redirect(url_for('index'))
        elif step == 1:
            # Пользователь вводит язык
            language = request.form.get('language', '').strip()
            if language:
                user['language'] = language
                user['step'] = 2
                session['user_data'] = user
            else:
                return render_template('error.html', message='Пожалуйста, введите язык.')
        elif step == 2:
            # Пользователь вводит тему
            topic = request.form.get('topic', '').strip()
            if topic:
                user['topic'] = topic
                # Генерация слов через OpenAI
                prompt = (
                    f"Составь список из 10 наиболее важных слов для изучения на тему '{user['topic']}' "
                    f"на языке {user['language']}. Укажи перевод на русский язык."
                )
                try:
                    response = openai.ChatCompletion.create(
                        model='gpt-3.5-turbo',
                        messages=[
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                    )
                    assistant_response = response['choices'][0]['message']['content'].strip()
                    print(f"Ответ от OpenAI: {assistant_response}")
                    # Парсинг ответа для извлечения слов
                    words = parse_words_from_response(assistant_response)
                    if not words:
                        raise ValueError("Не удалось распознать слова из ответа.")
                    user['words'] = words
                    user['step'] = 3
                    session['user_data'] = user
                except Exception as e:
                    error_message = f"Произошла ошибка при генерации слов: {e}"
                    print(error_message)
                    return render_template('error.html', message=error_message)
            else:
                return render_template('error.html', message='Пожалуйста, введите тематику.')
        elif step == 3:
            # Пользователь нажимает "Учить"
            if request.form.get('action') == 'учить':
                user['step'] = 4
                user['current_word_index'] = 0
                user['correct_answers'] = []
                session['user_data'] = user
        elif step == 4:
            # Пользователь выбирает вариант ответа
            selected_option = request.form.get('option')
            if selected_option:
                current_word = user['words'][user['current_word_index']]
                if selected_option.lower() == current_word['translation'].lower():
                    user['correct_answers'].append(current_word)
                    result = 'correct'
                else:
                    result = 'incorrect'
                user['current_word_index'] += 1
                if user['current_word_index'] >= len(user['words']):
                    user['step'] = 5
                session['user_data'] = user
                if user['step'] == 5:
                    # Все слова отвечены, переходим к шагу 5
                    return render_template(
                        'step4.html',
                        word=current_word['word'],
                        options=generate_options(current_word['translation'], user['words']),
                        result=result
                    )
                else:
                    # Переходим к следующему слову
                    return render_template(
                        'step4.html',
                        word=current_word['word'],
                        options=generate_options(current_word['translation'], user['words']),
                        result=result
                    )
            else:
                return render_template('error.html', message='Пожалуйста, выберите вариант ответа.')
        elif step == 5:
            # Обучение закончено
            if request.form.get('action') == 'finished':
                user['step'] = 2  # Возвращаемся к выбору темы
                session['user_data'] = user
        else:
            return render_template('error.html', message='Неизвестный шаг.')

    # Отображение соответствующего шаблона
    step = user['step']

    if step == 1:
        return render_template('step1.html')
    elif step == 2:
        return render_template('step2.html', language=user['language'])
    elif step == 3:
        return render_template('step3.html', language=user['language'], topic=user['topic'], words=user['words'])
    elif step == 4:
        if user['current_word_index'] < len(user['words']):
            current_word = user['words'][user['current_word_index']]
            options = generate_options(current_word['translation'], user['words'])
            return render_template('step4.html', word=current_word['word'], options=options)
        else:
            user['step'] = 5
            session['user_data'] = user
            # Все слова отвечены, отображаем шаг 5
            correct = len(user['correct_answers'])
            total = len(user['words'])
            return render_template('step5.html', correct_answers=correct, total_words=total)
    elif step == 5:
        correct = len(user['correct_answers'])
        total = len(user['words'])
        return render_template('step5.html', correct_answers=correct, total_words=total)
    else:
        return render_template('error.html', message='Неизвестный шаг.')

def parse_words_from_response(response_text):
    """
    Парсит текстовый ответ от OpenAI и извлекает слова и их переводы.
    Ожидается, что слова перечислены в виде:
    1. Слово - Перевод
    2. Слово - Перевод
    ...
    """
    words = []
    lines = response_text.strip().split('\n')
    for line in lines:
        # Убираем нумерацию и разбиваем слово и перевод
        if '. ' in line:
            line = line.split('. ', 1)[1]
        if ' - ' in line:
            parts = line.split(' - ', 1)
            if len(parts) == 2:
                word, translation = parts
                words.append({'word': word.strip(), 'translation': translation.strip()})
    return words

def generate_options(correct_translation, words):
    """
    Генерирует варианты ответов для текущего слова.
    Возвращает список из 3 вариантов: одно правильное и два случайных неправильных.
    """
    translations = [w['translation'] for w in words if w['translation'].lower() != correct_translation.lower()]
    options = random.sample(translations, min(2, len(translations)))
    options.append(correct_translation)
    random.shuffle(options)
    return options

@app.route('/reset', methods=['POST'])
def reset():
    session.pop('user_data', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)