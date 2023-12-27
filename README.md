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

pip install django-debug-toolbar==3.2.4  - тулбар для дебага (кол-во запросов)
pip install django-summernote  - редактор HTML
pip install django-filter  - django фильтры

python -m pip freeze > requirements.txt
python -m pip install -r requirements.txt

python manage.py test

# Запустит все тесты проекта
python3 manage.py test

# Запустит только тесты в приложении posts
python3 manage.py test posts

# Запустит только тесты из файла test_urls.py в приложении posts
python3 manage.py test posts.tests.test_urls

# Запустит только тесты из класса StaticURLTests для test_urls.py в приложении posts
python3 manage.py test posts.tests.test_urls.StaticURLTests

# Запустит только тест test_homepage()
# из класса StaticURLTests для test_urls.py в приложении posts
python3 manage.py test posts.tests.test_urls.StaticURLTests.test_homepage

python3 manage.py test
# Это то же самое, что
python3 manage.py test -v 1
Чтобы увидеть развёрнутый список пройденных и проваленных тестов — установите --verbosity 2:
python3 manage.py test -v 2
