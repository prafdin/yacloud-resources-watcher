from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/resources")],
            [KeyboardButton(text="/help")]
        ],
        resize_keyboard=True
    )
    return keyboard
