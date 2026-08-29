from datetime import datetime, timezone
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from app.db.session import AsyncSessionLocal
from app.core.config import settings

router = Router()

def is_admin(chat_id: int) -> bool:
    """Security check to restrict commands to admins only."""
    return str(chat_id) == settings.TELEGRAM_ADMIN_CHAT_ID

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    waiting_for_sheet = State()

def get_admin_keyboard():
    from app.core.config import settings
    buttons = [
        [InlineKeyboardButton(text="🔗 Привязать Google Таблицу", callback_data="btn_set_sheet")],
        [InlineKeyboardButton(text="📖 Инструкция Google Cloud", callback_data="btn_google_guide")]
    ]
    
    if settings.GOOGLE_SPREADSHEET_ID:
        url = f"https://docs.google.com/spreadsheets/d/{settings.GOOGLE_SPREADSHEET_ID}/edit"
        buttons.append([InlineKeyboardButton(text="📄 Открыть текущую таблицу", url=url)])
        
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.chat.id):
        await message.answer("Доступ запрещен.")
        return
    await message.answer(
        "Салют! Я бот аналитики монтажей. Выбери действие:",
        reply_markup=get_admin_keyboard()
    )



@router.callback_query(F.data == "btn_set_sheet")
async def cb_set_sheet(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.message.chat.id): return
    await callback.message.answer(
        "📄 *Официальная инструкция по работе с ботом InstallOps*\n\n"
        "1. Открой нужную Google Таблицу.\n"
        "2. Перейди в «Настройки доступа» (кнопка в правом верхнем углу).\n"
        "3. Добавь сервисный email с правами Редактора:\n`installops@installops.iam.gserviceaccount.com`\n"
        "4. Убери галочку «Уведомить пользователей».\n"
        "5. Перейди в «Настройки доступа» (кнопка в правом верхнем углу).\n"
        "6. Нажми копировать ссылку.", 
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_sheet)
    await callback.answer()

@router.callback_query(F.data == "btn_google_guide")
async def cb_google_guide(callback: CallbackQuery):
    if not is_admin(callback.message.chat.id): return
    await callback.message.answer(
        "☁️ *Пошаговая настройка Google Cloud (Создание сервисного аккаунта)*\n\n"
        "1. Зайди в Google Cloud Console (console.cloud.google.com).\n"
        "2. Создай новый проект (Create Project) и назови его, например, InstallOps.\n"
        "3. В боковом меню выбери «APIs & Services» ➔ «Library». Найди и включи **Google Sheets API**.\n"
        "4. Перейди в «APIs & Services» ➔ «Credentials».\n"
        "5. Нажми «Create Credentials» ➔ «Service Account».\n"
        "6. Введи имя (например, installops-bot) и нажми Done. Появится сервисный email.\n"
        "7. Нажми на созданный аккаунт, перейди во вкладку «Keys» ➔ «Add Key» ➔ «Create new key» ➔ Формат JSON.\n"
        "8. Скачанный файл открой в блокноте, скопируй весь текст и вставь его в переменную `GOOGLE_SERVICE_ACCOUNT_JSON` в настройках Railway.",
        parse_mode="Markdown"
    )
    await callback.answer()

import re
def update_env_variable(key: str, value: str):
    import os
    env_path = ".env"
    if not os.path.exists(env_path): return
    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            found = True
            break
    if not found:
        lines.append(f"\n{key}={value}\n")
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

@router.message(AdminStates.waiting_for_sheet)
async def process_sheet_url(message: Message, state: FSMContext):
    if not is_admin(message.chat.id): return
    
    url = message.text.strip()
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
    if not match:
        await message.answer("❌ Не могу найти ID таблицы в ссылке. Попробуй еще раз или жми /start для отмены.")
        return
        
    sheet_id = match.group(1)
    settings.GOOGLE_SPREADSHEET_ID = sheet_id
    update_env_variable("GOOGLE_SPREADSHEET_ID", sheet_id)
    
    await state.clear()
    
    from app.integrations.google.sheets import GoogleSheetsProvider
    try:
        sheets = GoogleSheetsProvider()
        await sheets.async_initialize()
        await message.answer(f"✅ Таблица успешно привязана!\nID: `{sheet_id}`\nВкладка 'Логи' и заголовки созданы автоматически.", parse_mode="Markdown", reply_markup=get_admin_keyboard())
    except Exception as e:
        await message.answer(f"⚠️ Таблица привязана, но не удалось её автоматически настроить. Убедись, что выдал права доступа.\nОшибка: {e}", reply_markup=get_admin_keyboard())

@router.message(F.text)
async def handle_group_messages(message: Message, state: FSMContext):
    if message.chat.type not in ["group", "supergroup"] and not is_admin(message.chat.id):
        return
        
    from app.integrations.telegram.chat_parser import ChatParser
    import time
    
    ticket = ChatParser.extract_ticket(message.text)
    is_postp = ChatParser.is_postponement_intent(message.text)
    
    data = await state.get_data()
    last_ticket = data.get("last_ticket")
    last_ticket_time = data.get("last_ticket_time", 0)
    current_time = time.time()
    
    final_ticket = None
    final_reason = None
    
    if ticket and is_postp:
        final_ticket = ticket
        final_reason = ChatParser.clean_reason(message.text, ticket)
        await state.update_data(last_ticket=None, last_ticket_time=0)
    elif ticket and not is_postp:
        await state.update_data(last_ticket=ticket, last_ticket_time=current_time)
        return
    elif not ticket and is_postp:
        if last_ticket and (current_time - last_ticket_time) <= 300:
            final_ticket = last_ticket
            final_reason = ChatParser.clean_reason(message.text, None)
            await state.update_data(last_ticket=None, last_ticket_time=0)
        else:
            return
    else:
        return
        
    if final_ticket:
        from app.models.pending import PendingEvent
        from app.models.employee import Employee
        from app.repositories import crud
        
        async with AsyncSessionLocal() as db:
            emp = await crud.get_employee_by_telegram_id(db, str(message.from_user.id))
            real_name = message.from_user.full_name or message.from_user.first_name or f"TG User {message.from_user.id}"
            if not emp:
                emp = Employee(
                    external_id=f"tg-{message.from_user.id}",
                    telegram_user_id=message.from_user.id,
                    name=real_name,
                    status="active"
                )
                db.add(emp)
            else:
                emp.name = real_name
            
            pending = PendingEvent(
                message_id=message.message_id,
                chat_id=message.chat.id,
                telegram_user_id=message.from_user.id,
                ticket_number=final_ticket,
                raw_text=message.text,
                extracted_reason=final_reason,
                status="pending"
            )
            db.add(pending)
            await db.commit()