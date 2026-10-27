import os
import random
import hashlib
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ChatJoinRequest, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

TOKEN = os.environ["BOT_TOKEN"]
BASE_URL = os.environ["RENDER_EXTERNAL_URL"]
PORT = int(os.getenv("PORT", "10000"))
SECRET = hashlib.sha256(TOKEN.encode()).hexdigest()[:32]

bot = Bot(TOKEN)
dp = Dispatcher()


@dp.chat_join_request()
async def on_join_request(req: ChatJoinRequest):
    a, b = random.randint(2, 9), random.randint(2, 9)
    answer = a + b
    options = {answer}
    while len(options) < 4:
        wrong = answer + random.randint(-4, 4)
        if wrong > 0:
            options.add(wrong)
    options = list(options)
    random.shuffle(options)

    buttons = [
        InlineKeyboardButton(
            text=str(o),
            callback_data=f"c:{req.chat.id}:{req.from_user.id}:{int(o == answer)}",
        )
        for o in options
    ]
    try:
        await bot.send_message(
            req.user_chat_id,
            f"👋 Привіт! Щоб підтвердити, що ви не бот, розв'яжіть приклад:\n\n<b>{a} + {b} = ?</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[buttons]),
            parse_mode="HTML",
        )
    except Exception:
        pass


@dp.callback_query(F.data.startswith("c:"))
async def on_answer(cb: CallbackQuery):
    _, chat_id, user_id, ok = cb.data.split(":")
    if cb.from_user.id != int(user_id):
        await cb.answer()
        return
    try:
        if ok == "1":
            await bot.approve_chat_join_request(int(chat_id), int(user_id))
            text = "✅ Капчу пройдено, вас прийнято до каналу!"
        else:
            await bot.decline_chat_join_request(int(chat_id), int(user_id))
            text = "❌ Неправильно. Заявку відхилено, можете подати нову."
    except TelegramBadRequest:
        text = "⚠️ Заявка вже недійсна. Подайте нову."
    try:
        await cb.message.edit_text(text)
    except Exception:
        pass
    await cb.answer()


async def on_startup(bot: Bot):
    await bot.set_webhook(
        f"{BASE_URL}/webhook",
        secret_token=SECRET,
        allowed_updates=["chat_join_request", "callback_query"],
        drop_pending_updates=False,
    )


async def health(request):
    return web.Response(text="ok")


def main():
    dp.startup.register(on_startup)
    app = web.Application()
    app.router.add_get("/", health)
    SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=SECRET).register(app, path="/webhook")
    setup_application(app, dp, bot=bot)
    web.run_app(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
