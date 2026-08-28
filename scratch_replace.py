import re

content = '''
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
                    telegram_user_id=str(message.from_user.id),
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
'''
with open('app/integrations/telegram/handlers.py', 'r', encoding='utf-8') as f:
    orig = f.read()
new_orig = re.sub(r'@router\.message\(F\.text\)\nasync def handle_group_messages.*', content.strip(), orig, flags=re.DOTALL)
with open('app/integrations/telegram/handlers.py', 'w', encoding='utf-8') as f:
    f.write(new_orig)
