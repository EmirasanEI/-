
import json
import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)

# Включаем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WORDS_FILE = "words.json"

# Загрузка слов из файла
def load_words():
    if not os.path.exists(WORDS_FILE):
        with open(WORDS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False)
    with open(WORDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# Сохранение слов в файл
def save_words(words):
    with open(WORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=2)

# Глобальное хранилище слов и состояний
WORDS = load_words()
user_states = {}

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я покажу слово на русском, а ты введи перевод на английском.")
    await ask_word(update)

# Отправить случайное слово
async def ask_word(update: Update):
    from random import choice
    if not WORDS:
        await update.message.reply_text("Словарь пуст. Добавь слова командой /add.")
        return
    word = choice(WORDS)
    user_states[update.effective_user.id] = word
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

    await ask_word(update)

# Команда /add
async def add_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace("/add", "").strip()
    if "-" not in text:
        await update.message.reply_text("Используй формат: слово - перевод\nНапример: кошка - cat")
        return
    russian, english = map(str.strip, text.split("-", 1))
    new_word = {"russian": russian, "english": english}
    WORDS.append(new_word)
    save_words(WORDS)
    await update.message.reply_text(f"Слово добавлено: {russian} - {english}")

# Запуск бота
async def main():
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        raise ValueError("BOT_TOKEN не установлен в переменных окружения.")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_word))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_answer))

    print("Бот запущен...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
