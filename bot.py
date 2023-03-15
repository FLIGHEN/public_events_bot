import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import logging
from aiogram.types import InputFile

from aiogram.types import BotCommand

import save_xls
import map_gen

admins = ["admin_ids"]

BOT_TOKEN = "TOKEN"


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Начать диалог"),
        BotCommand(command="/cancel", description="Отменить текущее действие")
    ]
    await bot.set_my_commands(commands)


async def main():
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(bot, storage=MemoryStorage())

    register_handlers_common(dp)
    register_handlers_map_gen(dp)
    register_handlers_admin(dp)

    await set_commands(bot)

    await dp.start_polling()


class CheckRadius(StatesGroup):
    waiting_for_agreement = State()
    waiting_for_center = State()
    # waiting_for_lon = State()
    waiting_for_radius = State()


def get_keyboard(message="", get_contact=False, get_location=False, chat_id=0, show_admin_button=True, question=False):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if question:
        button_yes = types.KeyboardButton("Да")
        button_no = types.KeyboardButton("Нет")
        keyboard.row(button_yes, button_no)
        keyboard.row(types.KeyboardButton("Отмена"))
    else:
        button = types.KeyboardButton(message, request_location=get_location,
                                      request_contact=get_contact)
        keyboard.add(button)
    if chat_id in admins and show_admin_button:
        data_button = types.KeyboardButton("📑база данных📑")
        map_button = types.KeyboardButton("🗺карта🗺")
        keyboard.row(data_button, map_button)
    return keyboard


# @dp.message_handler(commands=['start', 'help'])
# async def send_welcome(message: types.Message):
#    await message.reply("Привет!👋\nЯ location_bot!\nПришли мне свою геопозицию, нажав на кнопку снизу😄",
#                        reply_markup=get_keyboard(message="🗺Поделиться геопозицией🎯",
#                                                  get_contact=False,
#                                                  get_location=True,
#                                                  chat_id=message.chat.id))


async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.reply("Привет!👋\nЯ location_bot!\nПришли мне свою геопозицию, нажав на кнопку снизу😄",
                        reply_markup=get_keyboard(message="🗺Поделиться геопозицией🎯",
                                                  get_contact=False,
                                                  get_location=True,
                                                  chat_id=message.chat.id))


# @dp.message_handler(content_types=['text'])
async def handle_admin(message: types.Message):
    if message.chat.id in admins:
        if message.text == '🗺карта🗺':
            await message.answer("Выделить на определенном радиусе?", reply_markup=get_keyboard(show_admin_button=False,
                                                                                                get_contact=False,
                                                                                                get_location=True,
                                                                                                question=True,
                                                                                                chat_id=message.chat.id))
            await CheckRadius.waiting_for_agreement.set()
        elif message.text == '📑база данных📑':
            if os.path.exists("D:/PyCharm/maps/data.xlsx"):
                file = InputFile('data.xlsx')
                await message.answer_document(file)
            else:
                await message.reply("На данный момент никто не отправил геопозицию")


async def question_need_radius(message: types.Message, state: FSMContext):
    if message.text.lower() not in ['да', 'нет']:
        await message.answer("Пожалуйста, ответьте да или нет, используя клавиатуру ниже.")
        return
    if message.text.lower() == 'нет':
        await state.finish()
        await message.answer_document(open(map_gen.generate_map(save_xls.prepare_data())[0], 'rb'),
                                      reply_markup=get_keyboard(message="🗺Поделиться геопозицией🎯",
                                                                get_location=True,
                                                                chat_id=message.chat.id))
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(types.KeyboardButton('Отмена'))
        await CheckRadius.next()
        await message.answer("Укажите координаты центра в таком виде: (широта, долгота)", reply_markup=keyboard)


async def lat_lon_chosen(message: types.Message, state: FSMContext):
    if message.text.lower().find("(") != -1 and message.text.lower().find(")") != -1 \
            and message.text.lower().find(",") != -1:
        try:
            print(message.text[message.text.find("(") + 1:message.text.find(","):])
            print(message.text[message.text.find(",") + 1:message.text.find(")"):])
            await state.update_data(lat=float(message.text[message.text.find("(") + 1:message.text.find(","):]),
                                    lon=float(message.text[message.text.find(",") + 1:message.text.find(")"):]))

        except Exception as e:
            await message.answer("Пожалуйста, укажите координаты корректно: (широта, долгота)" + str(e))
            return
    else:
        await message.answer("Пожалуйста, укажите координаты корректно: (широта, долгота)")
        return
        # try:
    #    await state.update_data(lat=float(message.text))
    # except ValueError:
    #    await message.answer("Пожалуйста, укажите широту корректно")
    #   return
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton('Отмена'))
    await CheckRadius.next()
    await message.answer("Укажите радиус (в метрах)", reply_markup=keyboard)


# async def lon_chosen(message: types.Message, state: FSMContext):
#    try:
#        await state.update_data(lon=float(message.text))
#    except ValueError:
#        await message.answer("Пожалуйста, укажите долготу корректно")
#        return
#    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
#    keyboard.add(types.KeyboardButton('Отмена'))
#    await CheckRadius.next()
#    await message.answer("Укажите радиус (в метрах)", reply_markup=keyboard)


async def radius_chosen(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, укажите радиус корректно")
        return
    user_data = await state.get_data()
    print(user_data)
    info = map_gen.generate_map(save_xls.prepare_data(), check_rad=True,
                                center_lat=user_data.get('lat'),
                                center_lon=user_data.get('lon'),
                                radius=int(message.text))
    await message.answer_document(open(info[0],
                                       'rb'),
                                  reply_markup=get_keyboard(message="🗺Поделиться геопозицией🎯",
                                                            get_location=True,
                                                            chat_id=message.chat.id))
    if len(info[1]) > 0:
        try:
            await message.answer("в радиус вошли " + str(len(info[2])) + " человек:\n" + "\n".join(info[2]) + "\n\nв " \
                                                                                                              "радиус не "
                                                                                                              "вошли "
                                 + str(len(
                info[
                    1])) + " человек:\n" +
                                 "\n".join(info[1]))
        except Exception as e:
            print(e)
            await message.answer("в радиус вошли " + str(len(info[2])) + " человек" + "\n\nв радиус не вошли "
                                 + str(len(info[1])) +
                                 " человек")

    await state.finish()


# @dp.message_handler(content_types=['location'])
async def handle_location(message: types.Message):
    lat = message.location.latitude
    lon = message.location.longitude
    if message.from_user.full_name is not None:
        author = message.from_user.full_name
    elif message.from_user.username is not None:
        author = message.from_user.username
    else:
        author = "unidentified"
    time = message.date.strftime("%d/%m/%y %H:%M")
    chat_id = message.chat.id
   # reply = "широта:  {}\nдолгота: {}, message from: {}, time: {}, chat_id: {}".format(lat, lon, author, time,
   #                                                                                        message.chat.id)
    reply = "широта: {}\nдолгота: {}\nвремя отправки: {}".format(lat, lon, time)
    person_data = [lat, lon, author, time, chat_id]
    save_xls.add_data(person_data)
    await message.answer(reply, reply_markup=get_keyboard(message="🗺Поделиться геопозицией🎯",
                                                          get_contact=False,
                                                          get_location=True,
                                                          chat_id=message.chat.id))


async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Действие отменено", reply_markup=get_keyboard(message="🗺Поделиться геопозицией🎯",
                                                                        get_location=True,
                                                                        chat_id=message.chat.id))


def register_handlers_map_gen(dp: Dispatcher):
    dp.register_message_handler(question_need_radius, state=CheckRadius.waiting_for_agreement)
    dp.register_message_handler(lat_lon_chosen, state=CheckRadius.waiting_for_center)
    # dp.register_message_handler(lon_chosen, state=CheckRadius.waiting_for_lon)
    dp.register_message_handler(radius_chosen, state=CheckRadius.waiting_for_radius)


def register_handlers_common(dp: Dispatcher):
    dp.register_message_handler(cmd_start, commands="start", state="*")
    dp.register_message_handler(cmd_cancel, commands="cancel", state="*")
    dp.register_message_handler(cmd_cancel, lambda msg: msg.text.lower() == 'отмена', state="*")
    dp.register_message_handler(handle_location, content_types=['location'], state="*")


def register_handlers_admin(dp: Dispatcher):
    dp.register_message_handler(handle_admin, content_types=['text'], state="*")


# @dp.message_handler(content_types=['contact'])
# async def handle_contact(message: types.Message):
#    phone_number = message.contact.phone_number
#    reply = "phone number: {}".format(phone_number)
#    await message.answer(reply, reply_markup=types.ReplyKeyboardRemove())


if __name__ == '__main__':
    asyncio.run(main())
