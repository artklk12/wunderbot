def username_input(message):
    username = bot.send_message(message.chat.id, 'Введите логин')
    bot.register_next_step_handler(username, password_input)

def password_input(message):
    password = bot.send_message(message.chat.id, 'Введите пароль')
    bot.register_next_step_handler(password, login, message.text)

def login(password, username):
    try:
        wunder_token = requests.post(url="http://127.0.0.1:8000/api-token-auth/", json={"username": username, "password": password.text}).json()["token"]
        bot.send_message(password.chat.id, wunder_token)
        categories = requests.get(url="http://127.0.0.1:8000/api/v1/categories/",
                                  headers={"Authorization": f"Token {wunder_token}"})
        bot.send_message(password.chat.id, categories)
        print(categories.json())
    except:
        bot.send_message(password.chat.id, "Неправильный логин или пароль")
        username = bot.send_message(password.chat.id, 'Введите логин')
        bot.register_next_step_handler(username, password_input)