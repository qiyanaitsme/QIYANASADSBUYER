from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import aiosqlite


class ApplicationForm(StatesGroup):
    profile_link = State()
    source = State()
    experience = State()
    time_available = State()
    goals = State()
    telegram_link = State()


async def init_db():
    async with aiosqlite.connect('bot_database.db') as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            profile_link TEXT,
            source TEXT,
            experience TEXT,
            time_available TEXT,
            goals TEXT,
            telegram_link TEXT,
            status TEXT DEFAULT 'pending'
        )''')
        await db.execute('''CREATE TABLE IF NOT EXISTS blocked_users (
            user_id INTEGER PRIMARY KEY
        )''')
        await db.commit()


async def is_blocked(user_id):
    async with aiosqlite.connect('bot_database.db') as db:
        async with db.execute('SELECT * FROM blocked_users WHERE user_id = ?', (user_id,)) as cursor:
            return await cursor.fetchone() is not None


def is_admin(user_id, admin_ids):
    return user_id in admin_ids


async def main_menu(message: types.Message, admin_ids):
    if is_admin(message.from_user.id, admin_ids):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        buttons = ["📄 Просмотр активных заявок", "📑 Просмотр закрытых заявок"]
        keyboard.add(*buttons)

        await message.answer_photo(
            "https://cmsassets.rgpub.io/sanity/images/dsfx7636/news_live/e1c18b4d4b6ac4d33f1694279daef9c5b0517947-1920x1133.jpg",
            caption="Админ меню:",
            reply_markup=keyboard
        )
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        buttons = ["📝 Отправить заявку"]
        keyboard.add(*buttons)

        await message.answer_photo(
            "https://cdnb.artstation.com/p/assets/covers/images/044/177/039/large/suji-ye-suji-ye.jpg?1639316483",
            caption="Пользовательское меню:",
            reply_markup=keyboard
        )


async def start_application(message: types.Message):
    if await is_blocked(message.from_user.id):
        await message.reply("🚫 Вы заблокированы и не можете отправлять заявки.")
        return

    await message.reply("Введите ссылку на ваш профиль.")
    await ApplicationForm.profile_link.set()


async def process_profile_link(message: types.Message, state: FSMContext):
    await state.update_data(profile_link=message.text)
    await message.reply("Сумма за рекламу.")
    await ApplicationForm.source.set()


async def process_source(message: types.Message, state: FSMContext):
    await state.update_data(source=message.text)
    await message.reply(
        "Согласны ли Вы, что в случае Вашей блокировки Вы обязаны будете носить рекламу в профиле то количество времени, которое пробыли в бане?")
    await ApplicationForm.experience.set()


async def process_experience(message: types.Message, state: FSMContext):
    await state.update_data(experience=message.text)
    await message.reply(
        "Согласны ли Вы, что в случае получения более 5 баллов на форуме/READONLY Вы обязаны носить рекламу в профиле то количество времени, которое нужно для уменьшения количества баллов до 4 минимум.")
    await ApplicationForm.time_available.set()


async def process_time_available(message: types.Message, state: FSMContext):
    await state.update_data(time_available=message.text)
    await message.reply(
        "Согласны ли Вы что в случае досрочного прекращения сотрудничества Вы обязаны возместить ту сумму, которая будет высчитываться по формуле (Сумма за рекламу/Остаток дней)?")
    await ApplicationForm.goals.set()


async def process_goals(message: types.Message, state: FSMContext):
    await state.update_data(goals=message.text)
    await message.reply("Оставьте ссылку на телеграм-аккаунт, привязанный к вашему форумному аккаунту.")
    await ApplicationForm.telegram_link.set()


async def process_telegram_link(message: types.Message, state: FSMContext, admin_ids):
    await state.update_data(telegram_link=message.text)

    user_data = await state.get_data()

    if not all(key in user_data for key in
               ['profile_link', 'source', 'experience', 'time_available', 'goals', 'telegram_link']):
        await message.reply("Ошибка: не все данные заполнены. Попробуйте заново.")
        return

    async with aiosqlite.connect('bot_database.db') as db:
        cursor = await db.execute('''INSERT INTO applications (user_id, profile_link, source, experience, time_available, goals, telegram_link) 
                                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                                  (message.from_user.id, user_data['profile_link'], user_data['source'],
                                   user_data['experience'], user_data['time_available'], user_data['goals'],
                                   user_data['telegram_link']))
        application_id = cursor.lastrowid
        await db.commit()

    admin_message = f"📥 Пришла новая заявка. Заявка ID - {application_id}."
    for admin_id in admin_ids:
        await message.bot.send_message(admin_id, admin_message)

    await message.reply("✅ Ваша заявка отправлена!")
    await state.finish()


async def view_active_applications(message: types.Message, admin_ids):
    if not is_admin(message.from_user.id, admin_ids):
        await message.reply("У вас нет прав для выполнения этой команды.")
        return

    async with aiosqlite.connect('bot_database.db') as db:
        async with db.execute('SELECT * FROM applications WHERE status = "pending"') as cursor:
            applications = await cursor.fetchall()
            if not applications:
                await message.reply("Нет активных заявок.")
                return

            for app in applications:
                keyboard = InlineKeyboardMarkup()
                approve_button = InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{app[0]}")
                reject_button = InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{app[0]}")
                block_button = InlineKeyboardButton("🚫 Заблокировать", callback_data=f"block_{app[0]}")
                keyboard.add(approve_button, reject_button, block_button)

                await message.reply(f"ID заявки: {app[0]}\nПрофиль: {app[2]}\nИсточник: {app[3]}\nОпыт: {app[4]}\n"
                                    f"Статус: {app[6]}\nTG ID: {app[1]}\nСсылка на Telegram: {app[7]}",
                                    reply_markup=keyboard)


async def handle_decision_callback(callback_query: types.CallbackQuery, admin_ids):
    action, app_id = callback_query.data.split('_')
    app_id = int(app_id)

    async with aiosqlite.connect('bot_database.db') as db:
        if action == "approve":
            await db.execute('UPDATE applications SET status = "approved" WHERE id = ?', (app_id,))
            async with db.execute('SELECT user_id FROM applications WHERE id = ?', (app_id,)) as cursor:
                user_id = (await cursor.fetchone())[0]

            await callback_query.bot.send_photo(
                user_id,
                "https://cdna.artstation.com/p/assets/images/images/030/654/430/large/aa-ariel-.jpg?1601265647",
                caption="✅ Вас приняли!"
            )
            await callback_query.message.edit_text(f"Заявка {app_id} одобрена.")
        elif action == "reject":
            await db.execute('UPDATE applications SET status = "rejected" WHERE id = ?', (app_id,))
            async with db.execute('SELECT user_id FROM applications WHERE id = ?', (app_id,)) as cursor:
                user_id = (await cursor.fetchone())[0]

            await callback_query.bot.send_photo(
                user_id,
                "https://i.pinimg.com/736x/bb/59/30/bb5930f7d178be7ae223ecb018d9f70a.jpg",
                caption="❌ Вас не приняли."
            )
            await callback_query.message.edit_text(f"Заявка {app_id} отклонена.")
        elif action == "block":
            await db.execute('UPDATE applications SET status = "blocked" WHERE id = ?', (app_id,))
            async with db.execute('SELECT user_id FROM applications WHERE id = ?', (app_id,)) as cursor:
                user_id = (await cursor.fetchone())[0]

            await db.execute('INSERT INTO blocked_users (user_id) VALUES (?)', (user_id,))

            await callback_query.bot.send_photo(
                user_id,
                "https://i.ytimg.com/vi/pt5QoChilDU/maxresdefault.jpg",
                caption="🚫 Вы заблокированы."
            )
            await callback_query.message.edit_text(f"Пользователь {user_id} заблокирован.")
        await db.commit()


async def view_closed_applications(message: types.Message, admin_ids):
    if not is_admin(message.from_user.id, admin_ids):
        await message.reply("У вас нет прав для выполнения этой команды.")
        return

    async with aiosqlite.connect('bot_database.db') as db:
        async with db.execute(
                'SELECT * FROM applications WHERE status IN ("approved", "rejected", "blocked")') as cursor:
            applications = await cursor.fetchall()
            if not applications:
                await message.reply("Нет закрытых заявок.")
                return

            for app in applications:
                await message.reply(
                    f"ID: {app[0]}\nПрофиль: {app[2]}\nИсточник: {app[3]}\nОпыт: {app[4]}\nСтатус: {app[6]}")


def register_handlers(dp: Dispatcher, admin_ids):
    dp.register_message_handler(lambda message: main_menu(message, admin_ids), commands="start", state="*")
    dp.register_message_handler(start_application, text="📝 Отправить заявку", state="*")
    dp.register_message_handler(process_profile_link, state=ApplicationForm.profile_link)
    dp.register_message_handler(process_source, state=ApplicationForm.source)
    dp.register_message_handler(process_experience, state=ApplicationForm.experience)
    dp.register_message_handler(process_time_available, state=ApplicationForm.time_available)
    dp.register_message_handler(process_goals, state=ApplicationForm.goals)
    dp.register_message_handler(lambda message, state: process_telegram_link(message, state, admin_ids),
                                state=ApplicationForm.telegram_link)

    dp.register_message_handler(lambda message: view_active_applications(message, admin_ids),
                                text="📄 Просмотр активных заявок")
    dp.register_message_handler(lambda message: view_closed_applications(message, admin_ids),
                                text="📑 Просмотр закрытых заявок")
    dp.register_callback_query_handler(lambda callback_query: handle_decision_callback(callback_query, admin_ids),
                                       lambda c: c.data.startswith(('approve_', 'reject_', 'block_')))
