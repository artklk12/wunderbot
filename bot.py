import telebot
import requests
import sqlite3
from config import TOKEN
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

bot = telebot.TeleBot(TOKEN)

token="0d9ab7c360d64d7bf8c2175cd675007d67a0c205"

conn = sqlite3.connect('wunder_bot.db', check_same_thread=False)
cursor = conn.cursor()

@bot.message_handler(commands=['login'])
def username_input(message):
    username = bot.send_message(message.chat.id, "Введите логин")
    bot.register_next_step_handler(username, password_input)

def password_input(message):
    password = bot.send_message(message.chat.id, "Введите пароль")
    username = message.text
    bot.register_next_step_handler(password, login, username)

def login(message, username):
    password = message.text
    response = requests.post(url="http://127.0.0.1:8000/api-token-auth/", json={
        "username": username,
        "password": password
    })
    if response.ok:
        token = response.text.split(":")[1].lstrip('"').rstrip('"}')
        user = cursor.execute('SELECT * FROM users WHERE user_tg_id = ?', (message.from_user.id,))
        if user.fetchone() is None:
            cursor.execute('INSERT INTO users (user_tg_id, token) VALUES (?, ?)', (message.from_user.id, token))
            conn.commit()
        else:
            cursor.execute('UPDATE users SET token = ? WHERE user_tg_id = ?', (token, message.from_user.id))
            conn.commit()
        bot.send_message(message.chat.id, "Успешный вход")
    else:
        bot.send_message(message.chat.id, "Неверные логин или пароль")


@bot.message_handler(commands=['logout'])
def logout(message):
    token = get_token(message.chat.id)
    if token:
        cursor.execute('UPDATE users SET token = NULL WHERE user_tg_id = ?', (message.from_user.id,))
        conn.commit()
        bot.send_message(message.chat.id, "Вы успешно вышли из аккаунта")
    else:
        bot.send_message(message.chat.id, "Вы не вошли в аккаунт. Чтобы войти напишите /login")


def get_token(user_id):
    cursor.execute('SELECT token FROM users WHERE user_tg_id = ?', (user_id,))
    token = cursor.fetchone()[0]
    return token


@bot.message_handler(commands=['menu'])
def message_handler(message):
    token = get_token(message.chat.id)
    if token:
        keyboard = InlineKeyboardMarkup()
        keyboard.row_width = 2
        keyboard.add(InlineKeyboardButton("Показать категории", callback_data="Show_cats"))
        bot.send_message(message.chat.id, "Выберите действие", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "Вы не вошли в аккаунт. Чтобы войти напишите /login")

@bot.callback_query_handler(func=lambda call: call.data=="Show_cats")
def show_all_categories(call):
    token = get_token(call.from_user.id)
    if token:
        categories = requests.get(url="http://127.0.0.1:8000/api/v1/categories/", headers={"Authorization": f"Token {token}"}).json()
        keyboard = InlineKeyboardMarkup(row_width=2)
        buttons = []
        for item in categories:
            buttons.append(InlineKeyboardButton(f"{item['title']}", callback_data=f"Show_category:{item['id']}"))
        keyboard.add(*buttons)
        keyboard.add(InlineKeyboardButton("❇️Создать категорию", callback_data=f"Create_category"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Выберите категорию', reply_markup=keyboard)
    else:
        bot.send_message(call.from_user.id, "Вы не вошли в аккаунт. Чтобы войти напишите /login")

@bot.callback_query_handler(func=lambda call: call.data.startswith("Create_category"))
def create_category(call):
    token = get_token(call.from_user.id)
    if token:
        msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Введите название новой категории')
        bot.register_next_step_handler(msg, create_category_on_server)
    else:
        bot.send_message(call.from_user.id, "Вы не вошли в аккаунт. Чтобы войти напишите /login")

def create_category_on_server(msg):
    requests.post(url="http://127.0.0.1:8000/api/v1/categories/",
                  headers={"Authorization": f"Token {token}"},
                  json={"title": f"{msg.text}"})
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("⬅️ Назад", callback_data=f"Show_cats"))
    bot.send_message(msg.from_user.id, "Новая категория успешно создана", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("Show_category:"))
def show_category(call):
    token = get_token(call.from_user.id)
    cat_id = call.data.split("Show_category:")[1]
    tasks = requests.get(url=f"http://127.0.0.1:8000/api/v1/categories/{cat_id}/",
                              headers={"Authorization": f"Token {token}"}).json()
    keyboard = InlineKeyboardMarkup()
    for item in tasks:
        keyboard.add(InlineKeyboardButton(f"{item['title']}", callback_data=f"Show_task:{item['id']}"))
    keyboard.add(InlineKeyboardButton("❇️Создать задачу", callback_data=f"Create_task_in_cat:{cat_id}"))
    keyboard.add(InlineKeyboardButton("🗑️ Удалить категорию", callback_data=f"Delete_category:{cat_id}"))
    keyboard.add(InlineKeyboardButton("⬅️Назад", callback_data=f"Show_cats"))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Выберите задачу', reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("Delete_category:"))
def delete_category(call):
    token = get_token(call.from_user.id)
    cat_id = call.data.split("Delete_category:")[1]
    if token:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🗑️ Да", callback_data=f"Delete_category_on_server:{cat_id}"))
        keyboard.add(InlineKeyboardButton("Нет", callback_data=f"Show_category:{cat_id}"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Вы уверены, что хотите удалить категорию?', reply_markup=keyboard)
    else:
        bot.send_message(call.from_user.id, "Вы не вошли в аккаунт. Чтобы войти напишите /login")

@bot.callback_query_handler(func=lambda call: call.data.startswith("Delete_category_on_server:"))
def delete_category_on_server(call):
    token = get_token(call.from_user.id)
    cat_id = call.data.split("Delete_category_on_server:")[1]
    requests.delete(url=f"http://127.0.0.1:8000/api/v1/categories/{cat_id}/",
                              headers={"Authorization": f"Token {token}"})
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("⬅️Назад", callback_data=f"Show_cats"))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Категория успешно удалена', reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith("Create_task_in_cat:"))
def create_task(call):
    token = get_token(call.from_user.id)
    if token:
        cat_id = call.data.split("Create_task_in_cat:")[1]
        msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Введите название новой задачи')
        bot.register_next_step_handler(msg, create_task_on_server, cat_id)
    else:
        bot.send_message(call.from_user.id, "Вы не вошли в аккаунт. Чтобы войти напишите /login")

def create_task_on_server(msg, cat_id):
    requests.post(url=f"http://127.0.0.1:8000/api/v1/categories/{cat_id}/",
                  headers={"Authorization": f"Token {token}"},
                  json={"title": msg.text,
                        "category_id": cat_id})
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("⬅️Назад", callback_data=f"Show_category:{cat_id}"))
    bot.send_message(msg.from_user.id, "Новая задача успешно создана", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("Show_task:"))
def show_task(call):
    token = get_token(call.from_user.id)
    task_id = call.data.split("Show_task:")[1]
    task = requests.get(url=f"http://127.0.0.1:8000/api/v1/tasks/{task_id}",
                              headers={"Authorization": f"Token {token}"}).json()
    if task['is_done'] == True:
        condition = '✅'
    else:
        condition = '❌'

    if task['content'] == None:
        task['content'] = ''

    task_card = f"{condition} {task['title']} \n\n" \
           f"{task['content']} \n"
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("✏️Изменить", callback_data=f"Edit_task:{task_id}"),
                 (InlineKeyboardButton("🗑️ Удалить задачу", callback_data=f"Delete_task:{task_id}")))
    keyboard.add(InlineKeyboardButton("⬅️Назад", callback_data=f"Show_category:{task['category']}"))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=task_card, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("Delete_task:"))
def delete_task(call):
    token = get_token(call.from_user.id)
    task_id = call.data.split("Delete_task:")[1]
    if token:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🗑️ Да", callback_data=f"Delete_task_on_server:{task_id}"))
        keyboard.add(InlineKeyboardButton("Нет", callback_data=f"Show_task:{task_id}"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Вы уверены, что хотите удалить задачу?', reply_markup=keyboard)
    else:
        bot.send_message(call.from_user.id, "Вы не вошли в аккаунт. Чтобы войти напишите /login")

@bot.callback_query_handler(func=lambda call: call.data.startswith("Delete_task_on_server:"))
def delete_task_on_server(call):
    token = get_token(call.from_user.id)
    task_id = call.data.split("Delete_task_on_server:")[1]
    cat_id = requests.delete(url=f"http://127.0.0.1:8000/api/v1/tasks/{task_id}/",
                              headers={"Authorization": f"Token {token}"}).text
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("⬅️Назад", callback_data=f"Show_category:{cat_id}"))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Задача успешно удалена', reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith("Edit_task:"))
def edit_task(call):
    task_id = call.data.split("Edit_task:")[1]
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Название", callback_data=f"Target_task_edit_title:{task_id}"),
                 InlineKeyboardButton("Готовность", callback_data=f"Target_task_edit_is_done:{task_id}"),
                 InlineKeyboardButton("Описание", callback_data=f"Target_task_edit_content:{task_id}")
                 )
    keyboard.add(InlineKeyboardButton("⬅️Назад", callback_data=f"Show_task:{task_id}"))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Что будем менять?",
                          reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("Target_task_edit_title:"))
def target_task_edit_title(call):
    task_id = call.data.split("Target_task_edit_title:")[1]
    msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,  text="Введите новое значение")
    bot.register_next_step_handler(msg, update_data_title, task_id)

def update_data_title(msg, task_id):
    token = get_token(msg.from_user.id)
    requests.patch(url=f"http://127.0.0.1:8000/api/v1/tasks/{task_id}/",
                        headers={"Authorization": f"Token {token}"},
                        json={"title": f"{msg.text}"})
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("⬅️Назад", callback_data=f"Show_task:{task_id}"))
    bot.send_message(msg.chat.id, "Успешно обновлено", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith("Target_task_edit_content:"))
def target_task_edit_content(call):
    task_id = call.data.split("Target_task_edit_content:")[1]
    msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,  text="Введите новое значение")
    bot.register_next_step_handler(msg, update_data_content, task_id)

def update_data_content(msg, task_id):
    requests.patch(url=f"http://127.0.0.1:8000/api/v1/tasks/{task_id}/",
                        headers={"Authorization": f"Token {token}"},
                        json={"content": f"{msg.text}"})
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("⬅️Назад", callback_data=f"Show_task:{task_id}"))
    bot.send_message(msg.chat.id, "Успешно обновлено", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith("Target_task_edit_is_done:"))
def target_task_edit_is_done(call):
    task_id = call.data.split("Target_task_edit_is_done:")[1]

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Готово", callback_data=f"Target_task_edit_switch_to_done:{task_id}"),
                 InlineKeyboardButton("Не готово", callback_data=f"Target_task_edit_switch_to_not_done:{task_id}"))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Выберите новое значение", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith("Target_task_edit_switch_to_done:"))
def update_data_to_done(call):
    task_id = call.data.split("Target_task_edit_switch_to_done:")[1]
    requests.patch(url=f"http://127.0.0.1:8000/api/v1/tasks/{task_id}/",
                        headers={"Authorization": f"Token {token}"},
                        json={"is_done": True})

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("⬅️Назад", callback_data=f"Show_task:{task_id}"))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Успешно обновлено", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("Target_task_edit_switch_to_not_done:"))
def update_data_to_not_done(call):
    task_id = call.data.split("Target_task_edit_switch_to_not_done:")[1]
    requests.patch(url=f"http://127.0.0.1:8000/api/v1/tasks/{task_id}/",
                        headers={"Authorization": f"Token {token}"},
                        json={"is_done": False})
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("⬅️Назад", callback_data=f"Show_task:{task_id}"))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Успешно обновлено", reply_markup=keyboard)


bot.polling()