import logging
import sys
import asyncio
import csv
from aiogram import Bot, Dispatcher, types, Router, html
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiohttp
from os import getenv
from aiogram.enums import ParseMode
from sqlalchemy import create_engine, Column, Integer, String, Sequence
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from bs4 import BeautifulSoup
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

# Установите свой токен бота
TOKEN = "6597211233:AAGstMTkO1le_rD1JFlfX6kPF-4jlDlxMLg"

DATABASE_URL = 'sqlite:///site_parser.db'
engine = create_engine(DATABASE_URL, echo=True)
Base = declarative_base()


# Определение модели данных для пользователя
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    username = Column(String(50), nullable=False)
    state = Column(String(50), nullable=True)


# Определение модели данных для товара
class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, Sequence('product_id_seq'), primary_key=True)
    name = Column(String(255), nullable=False)
    price = Column(String(50), nullable=False)
    link = Column(String(255), nullable=False)
    availability = Column(String(50), nullable=False)
    info = Column(String(255), nullable=False)


# Создание таблиц в базе данных
Base.metadata.create_all(engine)


form_router = Router()


# Функционал состояний для FSM
class UserState(StatesGroup):
    waiting_for_name = State()
    waiting_for_category = State()
    waiting_my_answer = State()


# Обработчик команды /start
@form_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(UserState.waiting_for_name)
    await message.answer(
        "Привет! Для начала работы введите свое имя.",
        reply_markup=ReplyKeyboardRemove(),
    )


# Обработчик ввода имени пользователя
@form_router.message(UserState.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.set_state(UserState.waiting_for_category)
    user_name = message.text
    user = User(username=user_name)
    session = sessionmaker(bind=engine)()
    session.add(user)
    session.commit()
    await message.answer(
        f"Привет, {user_name}! Теперь вы можете ввести ссылку на категорию товара.",
        reply_markup=ReplyKeyboardRemove(),
    )

# Обработчик ввода ссылки на категорию
@form_router.message(UserState.waiting_for_category)
async def process_category(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user = sessionmaker(bind=engine)().query(User).filter(User.id == user_id).first()
    if user:
        category_link = message.text
        await message.answer("Пожалуйста, ожидайте завершения парсинга. Это может занять некоторое время.")
        await parse_category(user_id, category_link)
        await message.answer("Парсинг завершен. Результаты сохранены в файле products.csv.")
    else:
        await message.answer("Что-то пошло не так. Пожалуйста, начните снова с команды /start.")
#
#
# # Обработчик команды /help
# @form_router.message(commands=['help'])
# async def cmd_help(message: types.Message):
#     await message.answer("Доступные команды:\n"
#                          "/start - начать работу\n"
#                          "/help - получить справку")
#
#
# Функция парсинга категории
async def parse_category(user_id, category_link):
    async with aiohttp.ClientSession() as session:
        async with session.get(category_link) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            products = []
            for product_tag in soup.find_all('li', class_='col-xs-6 col-sm-4 col-md-3 col-lg-3'):
                product_link = product_tag.find('h3').a['href']
                product_name = product_tag.find('h3').a['title']
                product_page = await session.get(f'https://books.toscrape.com/catalogue/{product_link}')
                product_html = await product_page.text()
                product_soup = BeautifulSoup(product_html, 'html.parser')
                price = product_soup.find('p', class_='price_color').text
                availability = product_soup.find('p', class_='instock availability').text.strip()
                info = product_soup.find('meta', {'name': 'description'})['content']
                product = Product(name=product_name, price=price, link=product_link, availability=availability, info=info)
                products.append(product)
    await save_to_csv(products)


# Функция сохранения результатов в CSV
async def save_to_csv(products):
    with open('products.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Название', 'Цена', 'Ссылка', 'Наличие', 'Информация'])
        for product in products:
            writer.writerow([product.name, product.price, product.link, product.availability, product.info])

async def main():
    bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    dp.include_router(form_router)

    await dp.start_polling(bot)

# Запуск бота
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())

