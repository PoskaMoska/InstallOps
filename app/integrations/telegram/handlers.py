from datetime import datetime, timezone
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from app.db.session import AsyncSessionLocal
from app.analytics.engine import AnalyticsEngine
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
        [InlineKeyboardButton(text="📊 Статистика за месяц", callback_data="btn_stats")],
        [InlineKeyboardButton(text="🔗 Привязать Google Таблицу", callback_data="btn_set_sheet")]
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

@router.callback_query(F.data == "btn_stats")
async def cb_stats(callback: CallbackQuery):
    if not is_admin(callback.message.chat.id): return
    await callback.answer()
    # Просто переиспользуем функцию статистики, передав ей сообщение из коллбека
    await cmd_stats(callback.message)

@router.callback_query(F.data == "btn_set_sheet")
async def cb_set_sheet(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.message.chat.id): return
    await callback.message.answer(
        "🔗 **Привязка таблицы:**\n\n"
        "1. Открой свою таблицу.\n"
        "2. Нажми **«Настройки доступа»** в правом верхнем углу.\n"
        "3. Добавь эту почту как **Редактора**:\n"
        "`installops@installops.iam.gserviceaccount.com`\n"
        "4. Просто скинь мне ссылку на таблицу сюда в чат.\n\n"
        "Пример: `https://docs.google.com/spreadsheets/d/.../edit`", 
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_sheet)
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

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if not is_admin(message.chat.id):
        return
        
    now = datetime.now(timezone.utc)
    start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    async with AsyncSessionLocal() as db:
        engine = AnalyticsEngine(db)
        stats = await engine.calculate_period_stats(start_date=start_date, end_date=now)
    
    best_name = stats.best_employee.employee_name if stats.best_employee else "N/A"
    best_rate = f"{stats.best_employee.postponement_rate:.2f}%" if stats.best_employee else "N/A"
    
    worst_name = stats.worst_employee.employee_name if stats.worst_employee else "N/A"
    worst_count = stats.worst_employee.total_postponements if stats.worst_employee else 0
    
    text = (
        f"📊 <b>Статистика за текущий месяц</b>\n\n"
        f"Монтажей: {stats.total_installations}\n"
        f"Заказов с переносами: {stats.installations_with_postponement}\n"
        f"Всего переносов: {stats.total_postponements}\n"
        f"% переносов: {stats.postponement_rate:.2f}%\n\n"
        f"🏆 <b>Лучший показатель:</b>\n"
        f"{best_name} — {best_rate}\n\n"
        f"⚠️ <b>Больше всего переносов:</b>\n"
        f"{worst_name} — {worst_count}"
    )
    
    await message.answer(text, parse_mode="HTML")
    
@router.message(Command("employee"))
async def cmd_employee(message: Message):
    if not is_admin(message.chat.id):
        return
        
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Укажи имя монтажника: /employee Иван")
        return
        
    emp_name = parts[1].strip().lower()
    
    now = datetime.now(timezone.utc)
    start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    async with AsyncSessionLocal() as db:
        engine = AnalyticsEngine(db)
        stats = await engine.calculate_period_stats(start_date, now)
        
    target = next((e for e in stats.employees if emp_name in e.employee_name.lower()), None)
    
    if not target:
        await message.answer(f"Монтажник '{emp_name}' не найден.")
        return
        
    text = (
        f"👤 <b>{target.employee_name}</b>\n\n"
        f"Монтажей: {target.total_installations}\n"
        f"Заказов с переносами: {target.installations_with_postponement}\n"
        f"Всего переносов: {target.total_postponements}\n"
        f"% переносов: {target.postponement_rate:.2f}%\n\n"
        f"📋 <b>По причинам:</b>\n"
        f"Вина монтажника: {target.reasons_breakdown.get('employee_fault', 0)}\n"
        f"Клиент: {target.reasons_breakdown.get('client_request', 0)}\n"
        f"Техника: {target.reasons_breakdown.get('technical', 0)}\n"
        f"Материалы: {target.reasons_breakdown.get('materials', 0)}\n"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(F.text)
async def handle_group_messages(message: Message):
    """
    Listens to group messages, tries to parse a ticket and postponement intent.
    Creates a PendingEvent in DB if found.
    """
    # Слушаем только в группах ИЛИ в личных сообщениях, если это пишет админ (для тестов)
    if message.chat.type not in ["group", "supergroup"] and not is_admin(message.chat.id):
        return
        
    from app.integrations.telegram.chat_parser import ChatParser
    parsed = ChatParser.parse_message(message.text)
    
    if parsed:
        ticket_number, reason = parsed
        
        from app.models.pending import PendingEvent
        from app.models.employee import Employee
        from app.repositories import crud
        
        async with AsyncSessionLocal() as db:
            # 1. Update or create the Employee with their REAL Telegram name
            emp = await crud.get_employee_by_telegram_id(db, str(message.from_user.id))
            real_name = message.from_user.full_name or message.from_user.first_name or f"TG User {message.from_user.id}"
            
            if not emp:
                emp = Employee(
                    external_id=f"tg-{message.from_user.id}",
                    telegram_user_id=str(message.from_user.id),
                    name=real_name,
                    status="active"
                )
                db.add(emp)
            elif emp.name.startswith("TG User ") or emp.name == "Unknown":
                emp.name = real_name
            
            # 2. Save the pending event
            pending = PendingEvent(
                message_id=message.message_id,
                chat_id=message.chat.id,
                telegram_user_id=message.from_user.id,
                ticket_number=ticket_number,
                raw_text=message.text,
                extracted_reason=reason,
                status="pending"
            )
            db.add(pending)
            await db.commit()
            
            # Optionally, we can react to the message so the user knows it was caught
            # await message.reply("👀 Зафиксировал возможный перенос. Жду 10 минут...")

