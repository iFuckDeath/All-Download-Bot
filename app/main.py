import asyncio, logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from .config import load_settings
from .db import connect, init_db
from .handlers import setup

async def main():
    s = load_settings()
    logging.basicConfig(level=getattr(logging, s.log_level, logging.INFO),
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    bot = Bot(s.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    pool = await connect(s.database_url)
    await init_db(pool)
    dp = Dispatcher()
    dp.include_router(setup(s, pool))
    try:
        me = await bot.get_me()
        logging.getLogger(__name__).info("Starting bot as @%s", me.username)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await pool.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
