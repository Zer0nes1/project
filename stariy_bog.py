import logging
import telebot
import requests
import json
import matplotlib.pyplot as plt
import pandas as pd

from API import TOKEN

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы
STEAM_API_KEY = "32354B2FB29AAE9B9E01BEF6F03D464C"
NEWS_API_URL = "http://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/"  # API Steam News
GAME_DETAILS_API_URL = "http://store.steampowered.com/api/featuredcategories/"  # API Steam Game List

bot = telebot.TeleBot(TOKEN)
user_preferences = {}

# Функции работы с API
def get_game_news(appid, count=3, maxlength=300):
    try:
        response = requests.get(NEWS_API_URL, params={"appid": appid, "count": count, "maxlength": maxlength, "format": "json"})
        response.raise_for_status()
        data = response.json()
        return data.get("appnews", {}).get("newsitems", [])
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе API: {e}")
        return []

def get_game_info_steam(appid):
    try:
        url = f"http://store.steampowered.com/api/appdetails/"
        response = requests.get(url, params={"appids": appid})
        response.raise_for_status()
        data = response.json()
        if str(appid) in data and data[str(appid)]['success']:
            game_data = data[str(appid)]['data']
            return {
                "name": game_data.get("name"),
                "description": game_data.get("short_description"),
                "price": game_data.get("price_overview", {}).get("final_formatted", "Бесплатно"),
                "developers": ", ".join(game_data.get("developers", []))
            }
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе API Steam: {e}")
        return None

def get_top_games_steam():
    try:
        response = requests.get(GAME_DETAILS_API_URL)
        response.raise_for_status()
        data = response.json()["top_sellers"]
        return data["items"]
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе API Steam: {e}")
        return []

# Команды бота
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Привет! Я бот, который поможет найти информацию о компьютерных играх.\n\n" 
                          "/game <appid> - Найти информацию об игре\n" 
                          "/top - Показать топ игр\n" 
                          "/setgenre <жанр> - Установить предпочтительный жанр\n"
                          "/news <appid> - Получить последние новости по игре (ID в Steam)\n"
                          "/analis - Анализирует достижения в RoR2")

@bot.message_handler(commands=['game'])
def game_info(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "Пожалуйста, укажите appid игры после команды /game.")
        return

    appid = args[1]
    game = get_game_info_steam(appid)
    if game:
        bot.reply_to(message, f"Название: {game['name']}\nОписание: {game['description']}\nЦена: {game['price']}\nРазработчики: {game['developers']}")
    else:
        bot.reply_to(message, "Извините, информация об игре не найдена.")

@bot.message_handler(commands=['top'])
def top_games(message):
    games = get_top_games_steam()
    if games:
        reply = "Топ игр на Steam:\n"
        for game in games:
            reply += f"- {game['name']}\n"
        bot.reply_to(message, reply)
    else:
        bot.reply_to(message, "Не удалось получить список игр.")

@bot.message_handler(commands=['setgenre'])
def set_genre(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "Пожалуйста, укажите жанр после команды /setgenre.")
        return

    genre = args[1]
    chat_id = message.chat.id
    if chat_id not in user_preferences:
        user_preferences[chat_id] = {}
    user_preferences[chat_id]["genre"] = genre
    bot.reply_to(message, f"Предпочтительный жанр установлен: {genre}")

@bot.message_handler(commands=['news'])
def game_news(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "Пожалуйста, укажите appid игры после команды /news.")
        return

    appid = args[1]
    news_items = get_game_news(appid)
    if news_items:
        reply = "Последние новости:\n"
        for news in news_items:
            reply += f"- {news['title']}\n{news['url']}\n\n"
        bot.reply_to(message, reply)
    else:
        bot.reply_to(message, "Не удалось получить новости для данной игры.")

@bot.message_handler(commands=['analis'])
def analyze_achievements(message):
    try:
        # Получение данных об успехах
        raw = requests.get(
            "http://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v0002/",
            params={"gameid": 632360, "format": "json"}
        ).json()["achievementpercentages"]["achievements"]

        # Преобразование данных в DataFrame
        data = pd.DataFrame(raw)
        data = data.sort_values(by="percent", ascending=False)

        # Построение диаграммы
        plt.figure(figsize=(20, 10))
        plt.bar(data['name'], data['percent'], color='skyblue')
        plt.xlabel('Достижения', fontsize=12)
        plt.ylabel('Процент игроков', fontsize=12)
        plt.title('Распределение достижений в игре Risk of Rain 2', fontsize=14)
        plt.xticks(rotation=90)
        plt.tight_layout()

        # Сохранение диаграммы в файл
        chart_path = 'achievements_chart.png'
        plt.savefig(chart_path)
        plt.close()

        # Отправка диаграммы пользователю
        with open(chart_path, 'rb') as chart:
            bot.send_photo(message.chat.id, chart)
    except Exception as e:
        logger.error(f"Ошибка при анализе данных: {e}")
        bot.reply_to(message, "Произошла ошибка при анализе достижений.")

# Запуск бота
if __name__ == "__main__":
    bot.polling()
