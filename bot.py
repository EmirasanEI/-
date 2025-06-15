import json
import os
import logging
import re
from random import shuffle
from telegram import Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    ContextTypes, 
    filters
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

WORDS_FILE = "words.json"

# Загрузка слов из файла
def load_words():
    if not os.path.exists(WORDS_FILE):
        with open(WORDS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False)
        return []
    with open(WORDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# Сохранение слов в файл
def save_words(words):
    with open(WORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=2)

# Глобальное хранилище
WORDS = load_words()
user_states = {}
user_queues = {}  # Очередь слов для каждого пользователя

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_queues[user_id] = []  # Сбрасываем очередь при старте
    await update.message.reply_text(
        "Привет! Я покажу слово на русском, а ты введи перевод на английский.\n\n"
        "Можешь добавить несколько слов сразу:\n"
        "/add кот - cat, собака - dog\n"
        "или\n"
        "/add\n"
        "кот - cat\n"
        "собака - dog"
    )
    await ask_word(update, context)

# Отправка случайного слова из очереди
async def ask_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Если очередь пуста, создаем новую из всех слов
    if not user_queues.get(user_id):
        if not WORDS:
            await update.message.reply_text("Словарь пуст. Добавь слова командой /add.")
            return
        
        # Создаем перемешанную копию всех слов
        shuffled_words = WORDS.copy()
        shuffle(shuffled_words)
        user_queues[user_id] = shuffled_words
    
    # Берем следующее слово из очереди
    word = user_queues[user_id].pop()
    user_states[user_id] = word
    
    await update.message.reply_text(f"Переведи: {word['russian']}")

# Проверка ответа
async def check_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states:
        await update.message.reply_text("Нажми /start, чтобы начать.")
        return

    user_input = update.message.text.strip().lower()
    correct_answer = user_states[user_id]['english'].strip().lower()

    if user_input == correct_answer:
        await update.message.reply_text("✅ Правильно!")
    else:
        await update.message.reply_text(f"❌ Неправильно. Правильный ответ: {correct_answer}")

    await ask_word(update, context)

# Команда /add с поддержкой нескольких слов
async def add_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global WORDS  # Перемещено в самое начало функции
    
    text = update.message.text.replace("/add", "", 1).strip()
    
    # Если текст пустой, попробуем получить текст из reply
    if not text and update.message.reply_to_message:
        text = update.message.reply_to_message.text.strip()
    
    if not text:
        await update.message.reply_text(
            "Введите слова в формате:\n"
            "слово - перевод\n"
            "Можно несколько через запятую или с новой строки\n\n"
            "Пример:\n"
            "кот - cat\n"
            "собака - dog\n\n"
            "Или одной строкой:\n"
            "кот - cat, собака - dog"
        )
        return
    
    # Разбиваем текст на отдельные пары
    pairs = []
    if "\n" in text:
        # Многострочный ввод
        pairs = [line.strip() for line in text.split("\n") if line.strip()]
    else:
        # Однострочный ввод с разделителями
        pairs = [pair.strip() for pair in re.split(r'[,;]', text) if pair.strip()]
    
    added_words = []
    errors = []
    
    for i, pair in enumerate(pairs):
        if "-" not in pair:
            errors.append(f"Пара #{i+1}: '{pair}' - отсутствует дефис")
            continue
            
        parts = pair.split("-", 1)
        russian = parts[0].strip()
        english = parts[1].strip()
        
        if not russian:
            errors.append(f"Пара #{i+1}: отсутствует русское слово")
            continue
        if not english:
            errors.append(f"Пара #{i+1}: '{russian}' - отсутствует перевод")
            continue
            
        # Проверяем дубликаты
        if any(w['russian'] == russian for w in WORDS):
            errors.append(f"Пара #{i+1}: '{russian}' - слово уже существует")
            continue
            
        new_word = {"russian": russian, "english": english}
        added_words.append(new_word)
    
    # Добавляем слова в глобальный список
    if added_words:
        WORDS.extend(added_words)
        save_words(WORDS)
    
    # Формируем ответ
    response = ""
    if added_words:
        word_list = "\n".join([f"{w['russian']} - {w['english']}" for w in added_words])
        response += f"✅ Добавлено слов: {len(added_words)}\n{word_list}\n\n"
    
    if errors:
        response += f"❌ Ошибки ({len(errors)}):\n" + "\n".join(errors)
    
    await update.message.reply_text(response)

# Функция запуска бота
def main():
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        logger.error("BOT_TOKEN не установлен в переменных окружения.")
        raise ValueError("BOT_TOKEN не установлен")
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_word))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_answer))
    
    logger.info("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()
