import logging
import sys
import asyncio
import csv
from contextlib import contextmanager

from aiogram import Bot, Dispatcher, types, Router, html
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiohttp
from os import getenv
from aiogram.enums import ParseMode
from sqlalchemy import create_engine, Column, Integer, String, Sequence
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from bs4 import BeautifulSoup
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

# Установите свой токен бота
TOKEN = "6597211233:AAGstMTkO1le_rD1JFlfX6kPF-4jlDlxMLg"

DATABASE_URL = 'sqlite+aiosqlite:///site_parser.db'
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
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

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


form_router = Router()


#Session = sessionmaker(bind=engine)

@contextmanager
async def get_session():
    async_session = AsyncSession()
    try:
        yield async_session
        await async_session.commit()
    except Exception as e:
        await async_session.rollback()
        raise
    finally:
        await async_session.close()



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
# ...

@form_router.message(UserState.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.set_state(UserState.waiting_for_category)
    user_name = message.text
    user = User(username=user_name)
    session = sessionmaker(bind=engine)()
    session.add(user)
    #await session.commit()
    await message.answer(
        f"Привет, {user_name}! Теперь вы можете ввести ссылку на категорию товара.",
        reply_markup=ReplyKeyboardRemove(),
    )


# Обработчик ввода ссылки на категорию
@form_router.message(UserState.waiting_for_category)
async def process_category(message: Message, state: FSMContext):
    user_id = message.from_user.id

    try:
        # Используйте контекстный менеджер для работы с сессией
        async with get_session() as user_session:
            user = await user_session.query(User).filter(User.id == user_id).first()
            print(f"user: {user}")

            if user:
                category_link = message.text
                await message.answer("Пожалуйста, ожидайте завершения парсинга. Это может занять некоторое время.")
                await parse_category(user_id, category_link)
                await message.answer("Парсинг завершен. Результаты сохранены в файле products.csv.")
            else:
                print(f"User with id {user_id} not found or in an invalid state.")
                await message.answer("Что-то пошло не так. Пожалуйста, начните снова с команды /start.")
    except Exception as e:
        print(f"Exception: {e}")


# Обработчик команды /help
# @form_router.message(CommandHelp())
# async def cmd_help(message: Message, state: FSMContext):
#     await message.answer("Доступные команды:\n"
#                          "/start - начать работу\n"
#                          "/help - получить справку")


# Функция парсинга категории
async def parse_category(user_id, category_link):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(category_link) as response:
                category_html = await response.text()
                category_soup = BeautifulSoup(category_html, 'html.parser')

                products = []

                for product_tag in category_soup.find_all('li', class_='col-xs-6 col-sm-4 col-md-3 col-lg-3'):
                    product_link = product_tag.find('h3').a['href']
                    product_name = product_tag.find('h3').a['title']

                    async with session.get(f'https://books.toscrape.com/catalogue/{product_link}') as product_page:
                        product_html = await product_page.text()
                        product_soup = BeautifulSoup(product_html, 'html.parser')

                    price = product_soup.find('p', class_='price_color').text
                    availability = product_soup.find('p', class_='instock availability').text.strip()
                    info = product_soup.find('meta', {'name': 'description'})['content']

                    product = Product(name=product_name, price=price, link=product_link, availability=availability, info=info)
                    products.append(product)

        await save_to_csv(products)

    except Exception as e:
        print(f"Error during parsing: {e}")



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

