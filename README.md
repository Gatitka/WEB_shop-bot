# WEB_shop-bot
This is multy purpose platform uniting WEB shop and bots

####Активация среды окружения

Находясь в папке web_shop-bot ввести

source venv/Scripts/activate - активировать среду окружения
deactivate - деактивировать среду окружения

####Запуск проекта

Находясь в папке web_shop_with_bots

python manage.py runserver - запуск проекта
python manage.py load_menu - загрузить пресеты в базу данных

###Внести изменения в структуру базы данных (изменение моделей, создание новых таблиц)
python manage.py makemigrations
python manage.py migrate
