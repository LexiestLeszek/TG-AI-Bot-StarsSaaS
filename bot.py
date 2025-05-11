from together import Together
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# --- КОНСТАНТЫ ---
LLM_API = ''
TOKEN = ''
CHANNEL_ID = ''   
CHANNEL_LINK = '' 
PRICE_MON = 500   

# --- LLM ---
together_client = Together(api_key=LLM_API)
def ask_llm(user_prompt, system_prompt):
    response = together_client.chat.completions.create(
        model="deepseek-ai/DeepSeek-V3",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=1.1
    )
    return response.choices[0].message.content

# --- ПРОВЕРКА ПОДПИСКИ ---
async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        chat_member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        print(f"User {user_id} membership status: {chat_member.status}")
        return chat_member.status in ['member', 'administrator', 'creator', 'owner']
    except Exception as e:
        print(f"Error checking channel membership: {e}")
        return False

# --- ОТПРАВКА ПОДСКАЗКИ ПОДПИСАТЬСЯ ---
async def send_subscription_prompt(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton(f"{PRICE_MON} Stars ⭐ в месяц", url=CHANNEL_LINK)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = (
        "🔒 Доступ к боту предоставляется только по подписке.\n\n"
        f"Оплата: {PRICE_MON} Stars за безлимит на месяц.\n"
        "Нажмите на кнопку ниже, чтобы оформить подписку и сразу вернуться к общению."
    )
    await context.bot.send_message(chat_id=user_id, text=text, reply_markup=reply_markup)

# --- ХЕНДЛЕР /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    # сбросим сохранённую историю для данного пользователя
    context.user_data['history_str'] = ""
    text = (
        f"Привет, {user.first_name}! Я – твой ИИ бот 🤵‍♂️\n\n"
        "Задай мне вопрос и Я дам ответ, помня нашу историю диалога.\n"
        "Для продолжения нужно оплатить подписку"
    )
    await context.bot.send_message(chat_id=user.id, text=text)
    
async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await context.bot.send_message(chat_id=user.id, text='Чтобы отписаться, перейди в раздел "Мои Звезды" в настройках Telegram и отмени подписку там.')

# --- ХЕНДЛЕР ВСЕХ ТЕКСТОВЫХ СООБЩЕНИЙ ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_name = update.effective_user.name
    user_text = update.message.text
    
    print(f"[Msg] User {user_id} {user_name}: {user_text}\n")

    # 1. Проверяем подписку
    if not await check_subscription(user_id, context):
        await send_subscription_prompt(user_id, context)
        return
    
    SYSTEM_PROMPT = """
    Ты – бот.
    """
    
    # 3. Забираем текущую историю (или пустую)
    history_str = context.user_data.get('history_str', "")

    # 4. Добавляем новую строку от пользователя
    history_str += f"Пользователь: {user_text}\n"
    
    prompt_for_llm = f"""
    Сгенерируй ответ пользователю.
    Твоя история диалога c пользователем:

    {history_str}
    Корпоративный Макиавелли:
    """

     # 6. Пишем «печатает...» и зовём модель
    await context.bot.send_chat_action(chat_id=user_id, action="typing")
    try:
        assistant_text = ask_llm(prompt_for_llm, SYSTEM_PROMPT)
        print(f"[Msg] Bot: {assistant_text}\n")

        # 7. Добавляем ответ модели в историю
        history_str += f"Корпоративный Макиавелли: {assistant_text}\n"

        # 8. Сохраняем полную историю без усечения
        context.user_data['history_str'] = history_str

        # 9. Отправляем ответ пользователю
        await context.bot.send_message(chat_id=user_id, text=assistant_text)

    except Exception as e:
        print(f"LLM error: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text="⚠️ Произошла ошибка. Попробуйте чуть позже."
        )
    
# --- MAIN ---
def main() -> None:
    print("... bot started ...")
    application = Application.builder().token(TOKEN).build()

    # Регистрируем хендлеры
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запускаем бота
    application.run_polling()

if __name__ == "__main__":
    main()
