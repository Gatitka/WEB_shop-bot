import hashlib
import hmac
import time
import urllib.parse

BOT_TOKEN = "8465588029:AAEUflQ1NH2gukZXP6itcbu1561zubZQJNw"  # вставь свой
USER = {
    "id": 194602954,  # любой тестовый ID
    "first_name": "Natalia",
    "last_name": "Kirillova",
    "username": "Gatitka5",
    # "photo_url": "https://t.me/i/userpic/320/ivanpetrov.jpg",
}


def generate_hash(user_data, bot_token):
    # 1. auth_date — текущее время
    auth_date = int(time.time())
    user_data["auth_date"] = auth_date

    # 2. готовим data_check_string
    data_check_arr = [f"{k}={v}" for k, v in sorted(user_data.items())]
    data_check_string = "\n".join(data_check_arr)

    # 3. секретный ключ = sha256(bot_token)
    secret_key = hashlib.sha256(bot_token.encode()).digest()

    # 4. считаем hmac sha256
    hmac_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    # 5. добавляем hash в user_data
    user_data["hash"] = hmac_hash

    return user_data

# --- генерим тестовый payload ---
data = generate_hash(USER.copy(), BOT_TOKEN)

# формируем query строку
query = urllib.parse.urlencode(data)
url = f"http://localhost:8000/api/v1/telegram/link/?{query}"

print("\n✅ Тестовый запрос:")
print(url)
