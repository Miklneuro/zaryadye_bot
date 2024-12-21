import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForQuestionAnswering
from fuzzywuzzy import fuzz
from gtts import gTTS
import os
import glob
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from config import TOKEN  # Убедитесь, что у вас есть файл config.py с определенной переменной TOKEN

# Загрузка данных
CSV_PATH = r"C:\Users\Mikl\zaryadye_bot\60861CSV\data-60861-2024-08-06.csv"
df_plants = pd.read_csv(CSV_PATH, sep=';', encoding='utf-8', on_bad_lines='skip')
df_plants = df_plants[df_plants['ID'] != 'Код'].reset_index(drop=True)

# Загрузка модели BERT
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
model = AutoModelForQuestionAnswering.from_pretrained("bert-base-uncased")

# Функция озвучивания текста
def text_to_speech(text):
    tts = gTTS(text=text, lang='ru')
    audio_path = 'response.mp3'
    tts.save(audio_path)
    return audio_path

# Функция получения изображений растений
def get_plant_images(latin_name):
    image_dir = f'C:/Users/Mikl/zaryadye_bot/plant_images/{latin_name}'
    if os.path.exists(image_dir):
        return sorted(glob.glob(f'{image_dir}/Image_*.jpg'))
    return []

# Функция получения информации о растениях
def get_plant_info(question):
    # Обработка общих запросов о хвойных растениях
    if 'хвойные' in question.lower():
        conifer_plants = df_plants[df_plants['LandscapingZone'].str.contains('Хвойный', na=False)]
        response = "Хвойные растения в парке:\n" + "\n".join(conifer_plants['Name'].tolist())
        return response, True

    # Обработка запроса о смешанных лесах
    if 'смешанный лес' in question.lower():
        mixed_forest = df_plants[df_plants['LandscapingZone'].str.contains('Смешанный', na=False)]
        response = "Растения смешанного леса:\n" + "\n".join(mixed_forest['Name'].tolist())
        return response, True

    # Обработка запроса о всех растениях
    if 'все растения' in question.lower() or 'список растений' in question.lower():
        response = "Растения в парке:\n" + "\n".join(df_plants['Name'].tolist())
        return response, True

    # Нечеткое соответствие для названий растений
    max_ratio = 0
    matched_name = None
    for name in df_plants['Name'].unique():
        ratio = fuzz.partial_ratio(name.lower(), question.lower())
        if ratio > max_ratio and ratio > 70:
            max_ratio = ratio
            matched_name = name

    if matched_name:
        plant = df_plants[df_plants['Name'] == matched_name].iloc[0]
        latin_name = plant['LatinName']
        images = get_plant_images(latin_name)

        # Определение ответа на основе вопроса
        if any(word in question.lower() for word in ['где', 'расположен', 'растет']):
            response = f"{matched_name} расположен в {plant['LocationPlace']}."
        elif any(word in question.lower() for word in ['когда', 'цветет', 'цветение']):
            response = f"{matched_name} цветет в период: {plant['ProsperityPeriod']}."
        elif 'латинск' in question.lower():
            response = f"Латинское название {matched_name}: {plant['LatinName']}."
        else:
            response = f"{matched_name} (латинское название: {latin_name})\n{plant['Description']}"

        return response, images

    return "Растение не найдено.", []

# Основные обработчики команд
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Привет! Я бот для консультации по растениям парка Зарядье. Задайте мне вопрос.")

def handle_message(update: Update, context: CallbackContext):
    question = update.message.text
    response, images = get_plant_info(question)

    if images:
        update.message.reply_text(response)
        for img in images:
            with open(img, 'rb') as image_file:
                update.message.reply_photo(photo=image_file)
    else:
        update.message.reply_text(response)

    # Озвучивание
    audio_path = text_to_speech(response)
    with open(audio_path, 'rb') as audio_file:
        update.message.reply_audio(audio_file)

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()