import asyncio
import logging
import requests
from lxml import html
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode, ReplyKeyboardMarkup, KeyboardButton
from aiogram import executor

API_TOKEN = ...  # Замените на свой токен

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

url = 'http://cacs.socio.msu.ru/index.php?selst=21689'
response = requests.get(url)
tree = html.fromstring(response.content)


def get_schedule_one_day(table_element):
    def get_time_interval(lesson_number):
        time_intervals = {
            1: '09:00 — 10:30',
            2: '10:45 — 12:15',
            3: '13:00 — 14:30',
            4: '14:45 — 16:15',
            5: '16:30 — 18:00',
            6: '18:30 — 20:00',
            7: '20:10 — 21:40'
        }
        return time_intervals.get(lesson_number, 'Unknown Time')

    schedule_one_day = {}
    one_day_html = html.tostring(table_element[0], pretty_print=True)
    soup = BeautifulSoup(one_day_html, 'html.parser')

    date = soup.find('tr').find('td').text
    schedule_one_day[date] = {}

    tr_tags = soup.find_all('tr')[1:]  # Start from the second row to skip the first "Нет пары"

    current_lesson = 1

    for tr_tag in tr_tags:
        div_tag = tr_tag.find('div', class_='AREATXT1')
        if div_tag:
            subject = div_tag.find('div').get('title', 'No title')

            auditory_match = re.search(r'<b>(\d+)<\/b>', str(div_tag))
            auditory = auditory_match.group(1) if auditory_match else 0

            time_interval = get_time_interval(current_lesson)
            schedule_one_day[date][time_interval] = [subject, int(auditory)]
            current_lesson += 1
        else:
            time_interval = get_time_interval(current_lesson)
            schedule_one_day[date][time_interval] = ['Нет пары']
            current_lesson += 1

    return schedule_one_day


month = []
for week in range(1, 8):
    for day in range(2, 7):
        table_element = tree.xpath(f'/html/body/table/tr[1]/td/table/tr[3]/td[3]/table[2]/tr[3]/td[2]/table[2]/tr[{int(week)}]/td[{int(day)}]/table')
        month.append(get_schedule_one_day(table_element))

month = [item for item in month if '\xa0' not in item]
month_sorted = sorted(month, key=lambda x: list(x.keys())[0] if x.keys() else '')
sorted_month = sorted(month_sorted, key=lambda x: datetime.strptime(list(x.keys())[0], '%d.%m.%Y'))



def format_schedule(schedule):
    result = ""

    for date, classes in schedule.items():
        result += f"<b>{date}:</b>\n"

        if isinstance(classes, list):
            for time, lesson in classes.items():
                if isinstance(lesson, list):
                    subject = f"<b>{lesson[0]}</b>"
                    if len(lesson) > 1:
                        result += f"  {time}: {subject}, Ауд. {lesson[1]}\n"
                    else:
                        result += f"  {time}: {subject}\n"
                else:
                    result += f"  {time}: {lesson}\n"
        else:
            for time, lesson in classes.items():
                subject = f"<b>{lesson[0]}</b>"
                if len(lesson) > 1:
                    result += f"  {time}: {subject}, Ауд. {lesson[1]}\n"
                else:
                    result += f"  {time}: {subject}\n"

        result += "\n"

    return result


today = datetime.today().strftime('%d.%m.%Y')
tomorrow = (datetime.today() + timedelta(days=1)).strftime('%d.%m.%Y')


def get_today_schedule():
    today_schedule = None
    for day_schedule in month_sorted:
        if today in day_schedule:
            today_schedule = {today: day_schedule[today]}
            break
    return today_schedule


def get_tomorrow_schedule():
    tomorrow_schedule = None
    for day_schedule in month_sorted:
        if tomorrow in day_schedule:
            tomorrow_schedule = {tomorrow: day_schedule[tomorrow]}
            break
    return tomorrow_schedule


def get_this_week_schedule():
    current_date = datetime.today()
    start_of_week = current_date - timedelta(days=current_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    schedule_for_week = {}
    for day_schedule in month_sorted:
        date = list(day_schedule.keys())[0]
        date_obj = datetime.strptime(date, '%d.%m.%Y')
        if start_of_week <= date_obj <= end_of_week:
            schedule_for_week[date] = day_schedule[date]
    return schedule_for_week


def get_next_week_schedule():
    current_date = datetime.today()
    start_of_next_week = current_date + timedelta(days=(7 - current_date.weekday()))
    end_of_next_week = start_of_next_week + timedelta(days=6)
    schedule_for_next_week = {}
    for day_schedule in month_sorted:
        date = list(day_schedule.keys())[0]
        date_obj = datetime.strptime(date, '%d.%m.%Y')
        if start_of_next_week <= date_obj <= end_of_next_week:
            schedule_for_next_week[date] = day_schedule[date]
    return schedule_for_next_week


keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
buttons = [
    KeyboardButton(text="Сегasdsadasодня."),
    KeyboardButton(text="Завтра"),
    KeyboardButton(text="Эта неделя"),
    KeyboardButton(text="Следующая неделя"),
]
keyboard.add(*buttons)


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.answer("Привет! Я твой личный бот для получения расписания. Выбирай опцию.", reply_markup=keyboard)


@dp.message_handler(lambda message: message.text in ["Сегодня", "Завтра", "Эта неделя", "Следующая неделя"])
async def get_schedule(message: types.Message):
    # Получите расписание в зависимости от выбора пользователя
    if message.text == "Сегодня":
        schedule = get_today_schedule()
    elif message.text == "Завтра":
        schedule = get_tomorrow_schedule()
    elif message.text == "Эта неделя":
        schedule = get_this_week_schedule()
    elif message.text == "Следующая неделя":
        schedule = get_next_week_schedule()

    # Отправка расписания пользователю
    await message.answer(format_schedule(schedule), parse_mode=ParseMode.HTML)



if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
