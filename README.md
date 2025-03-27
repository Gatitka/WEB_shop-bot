# YUME SUSHI
Multy purpose platform uniting WEB shop and bots

Python 3.11
Django 4.1
PostgreSQL 14 (+ PostGIS)
Docker
Nginx

## Развертывание Docker Network для backend
#### Арихитектура проекта
Для запуска бэкэнда в сети контейнеров Docker необходимо организовать папки проекта следующим образом:
- YUMI_SUSHI
    - infra/
        - redis/
            - redis.conf
        - .env
        - backup.sh

    - logging/
        - cronlogfile.log

    - frontend/
    - docs/
    - media/
    - email/
    - backups/
    - docker-compose.production.yml

#### .env файл
Django не запустится без него!
```
SECRET_KEY=
DEBUG=True

TEST_SERVER=
PROTOCOL=http
DOMAIN=localhost:3000
ENVIRONMENT=development

DB_ENGINE_EX=django.db.backends.postgresql
DB_ENGINE=django.contrib.gis.db.backends.postgis
POSTGRES_DB=yume_db
POSTGRES_USER=
POSTGRES_PASSWORD=
DB_HOST=db
DB_PORT=5432

DB_FILE=db.sqlite3

SITE_NAME=yumesushi.rs
EMAIL_HOST=smtp.gmail.com
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_PORT=587

GOOGLE_API_KEY=
SENTRY_DSN=

BOT_TOKEN=
ADMIN_ID=
```

Из папки /YUMI_SUSHI набрать команды при запущенном Docker
```
docker compose -f docker-compose.production.yml up
docker compose -f docker-compose.production.yml exec backend python manage.py migrate
docker compose -f docker-compose.production.yml exec backend python manage.py load_all
docker compose -f docker-compose.production.yml exec backend python manage.py collectstatic
docker compose -f docker-compose.production.yml exec backend cp -r /app/web_shop_with_bots/static/. /backend_static/static/
docker compose -f docker-compose.production.yml exec backend cp -r /app/web_shop_with_bots/media/. /media/

```

Проект запустится в 4 контейнерах:
- nginx (прокси)
- backend (Django)
- db (PostgreSQL + Postgis)
- redis

Волюмы / доступны контейнерам
- media  / nginx, backend     - фото блюд, промо и пр
- static / nginx, backend     - статика бэкэнда
- yume_db_volume / db         - база данных

Фронтэнд клонируется из Git
В папке фронта необходимо создать .env файл с переменными
```
REACT_APP_GOOGLE_API_KEY=
REACT_APP_URL_DB='http://127.0.0.1:8000/'       для локального запуска
REACT_APP_URL_DB='https://your_server_name.com/'       для запуска на сервере
```

запускается
```
npm start
```



## Настройка backend из репозитория Git
#### Активация среды окружения

Папка проекта предполагает иметь следующую архитектуру:
- YUME SUSHI
    - infra/
        - .env
    - <файл>.yml
    - frontend
    - backend

Репозиторий бэкэнда склонировать в папку с названием backend.
внутри нее организовать виртуальное окружение проекта в папке /venv
```
python -m venv venv                      # создание среды окружения
source venv/Scripts/activate             # активировать среду окружения
deactivate                               # деактивировать среду окружения
```

#### Настройка проекта
##### Файл .env с переменными окружения
Для запуска проекта ЛОКАЛЬНО необходимо создать файл с чувствительными данными.
В папке проекта (на одном уровне с папкой backend) создать папку infra и в ней файл .env со следующими переменными.
Django не запустится без них!
```
SECRET_KEY=
DEBUG=True

TEST_SERVER=
PROTOCOL=http
DOMAIN=localhost:3000
ENVIRONMENT=
DEVELOPER=

ACCESS_TOKEN_LIFETIME=
REFRESH_TOKEN_LIFETIME=

DB_ENGINE_EX=django.db.backends.postgresql
DB_ENGINE=django.contrib.gis.db.backends.postgis
POSTGRES_DB=yume_db
POSTGRES_USER=
POSTGRES_PASSWORD=
DB_HOST=localhost
DB_PORT=5432

DB_FILE=db.sqlite3

SITE_NAME=yumesushi.rs
EMAIL_HOST=smtp.gmail.com
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_PORT=587

GOOGLE_API_KEY=
SENTRY_DSN=

BOT_TOKEN=
ADMIN_ID=
CHAT_ID=

CONSOLE_LOG_LEVEL=DEBUG
FILE_LOG_LEVEL=DEBUG
API_LOG_LEVEL=DEBUG
CATALOG_LOG_LEVEL=DEBUG
DELIVERY_LOG_LEVEL=DEBUG
PROMOS_LOG_LEVEL=DEBUG
SHOP_LOG_LEVEL=DEBUG
TM_BOT_LOG_LEVEL=DEBUG
USERS_LOG_LEVEL=DEBUG
SESSION_COOKIE_AGE=21600
```

##### Установка пакетов
Для запуска проекта необходимо установить все сторонние пакеты, описанные в requirements.txt.
Находясь в папке с requirements.txt ввести
```
python -m pip install -r requirements.txt
```
##### Создание или внесение изменений в базу данных
При запущенной PostgreSQL 14 и созданной базе данных yume_db,
перейти в корневую папку проекта web_shop_with_bots (уровень файла manage.py), сделать миграции и загрузит дами данные.
```
python manage.py makemigrations - создание макета изменений
python manage.py migrate - применение изменений
python manage.py load_all - загрузить пресеты в базу данных
```

#### Запуск проекта
Находясь в папке web_shop_with_bots
```
python manage.py runserver - запуск проекта
```
БЭКЭНД ЗАПУЩЕН и доступен по адресу http://127.0.0.1:8000/admin/

##### Дополнительные пакеты и команды для справки (установятся автоматически из requirements.txt )
```
pip install django-debug-toolbar==3.2.4  - тулбар для дебага (кол-во запросов)
pip install django-summernote  - редактор HTML
pip install django-filter  - django фильтры
python -m pip freeze > requirements.txt - сохранение пакетов в requirements.txt
```

## Навигация проекта
Для входа в раздел администратора по адресу http://0.0.0.0/admin/
логин: a@a.ru
пароль: adminadmin0

По эндпоинту http://0.0.0.0/redoc подключена документация API. В ней описаны шаблоны запросов к API и ответы. Для каждого запроса указаны уровни прав доступа - пользовательские роли, которым разрешён запрос.

Все эндоинты бизнес логики проходят через api/v1/

-**api/v1/auth/**
регистрация, авторизация, личный кабинет, JWT токены
-**api/v1/me/**
часть личного кабинета - "мои заказы", "мои адреса"

-**api/v1/menu/**
просмотр основного меню, добавление в корзину

-**api/v1/contacts/**
информация о ресторанах и условиях доставки

-**api/v1/promonews/**
промо новости

-**shopping_cart**
корзина покупок

-**api/v1/create_order_delivery/**
создание заказа на доставку
-**api/v1/create_order_delivery/pre_checkout/**
предвариательный просчет заказа на доставку

-**api/v1/create_order_takeaway/**
создание заказа на самовывоз
-**api/v1/create_order_takeaway/pre_checkout/**
предвариательный просчет заказа на самовывоз

Внутренние адреса для админки
-**api/v1/get_google_api_key/**
получение GOOGLE_API_KEY для обработки адресов
-**api/v1/get_user_data/**
получение данных о клиенте для автозаполнения формы заказа
-**api/v1/calculate_delivery/**
получение зоны доставки и стоимость доставки с учетом суммы заказа
или скидки на самовывооз



## Работа с тестами проекта
```
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
```








sudo apt update
sudo apt upgrade -y
sudo apt install python3-pip python3-venv git -y
sudo apt install nginx -y
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw enable
sudo ufw status
sudo systemctl start nginx
sudo nano /etc/nginx/sites-enabled/default



#### Арихитектура проекта
Для запуска бэкэнда в сети контейнеров Docker необходимо организовать папки проекта следующим образом:
- YUMI_SUSHI
    - infra/
        - .env
    - frontend/
    - docker-compose.production.yml

#### .env файл
Django не запустится без него!
```
SECRET_KEY=
DEBUG=True

TEST_SERVER=
PROTOCOL=http
DOMAIN=localhost:3000
ENVIRONMENT=development

DB_ENGINE_EX=django.db.backends.postgresql
DB_ENGINE=django.contrib.gis.db.backends.postgis
POSTGRES_DB=yume_db
POSTGRES_USER=
POSTGRES_PASSWORD=
DB_HOST=db
DB_PORT=5432

DB_FILE=db.sqlite3

SITE_NAME=yumesushi.rs
EMAIL_HOST=smtp.gmail.com
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_PORT=587

GOOGLE_API_KEY=
SENTRY_DSN=

BOT_TOKEN=
ADMIN_ID=
```

Из папки /YUMI_SUSHI набрать команды при запущенном Docker
```
docker compose -f docker-compose.production.yml up
docker compose -f docker-compose.production.yml exec backend python manage.py migrate
docker compose -f docker-compose.production.yml exec backend python manage.py load_all
docker compose -f docker-compose.production.yml exec backend python manage.py collectstatic
docker compose -f docker-compose.production.yml exec backend cp -r /app/web_shop_with_bots/static/. /backend_static/static/
docker compose -f docker-compose.production.yml exec backend cp -r /app/web_shop_with_bots/media/. /media/

```

Проект запустится в 3 контейнерах:
- nginx (прокси)
- backend (Django)
- db (PostgreSQL + Postgis)

Волюмы / доступны контейнерам
- media  / nginx, backend     - фото блюд, промо и пр
- static / nginx, backend     - статика бэкэнда
- yume_db_volume / db         - база данных

Фронтэнд клонируется из Git
В папке фронта необходимо создать .env файл с переменными
```
REACT_APP_GOOGLE_API_KEY=
REACT_APP_URL_DB='http://127.0.0.1:8000/'       для локального запуска
REACT_APP_URL_DB='https://your_server_name.com/'       для запуска на сервере
```

запускается
```
npm start
```



## Настройка backend из репозитория Git
#### Активация среды окружения

Папка проекта предполагает иметь следующую архитектуру:
- YUME SUSHI
    - infra/
        - .env
    - frontend
    - backend

Репозиторий бэкэнда склонировать в папку с названием backend.
внутри нее организовать виртуальное окружение проекта в папке /venv
```
python -m venv venv                      # создание среды окружения
source venv/Scripts/activate             # активировать среду окружения
deactivate                               # деактивировать среду окружения
```

#### Настройка проекта для разработки фронта (вся медиа и статика внутри)
##### Файл .env с переменными окружения
Для запуска проекта ЛОКАЛЬНО необходимо создать файл с чувствительными данными.
В папке проекта (на одном уровне с папкой backend) создать папку infra и в ней файл .env со следующими переменными.
Django не запустится без них!
```
SECRET_KEY=
DEBUG=True

TEST_SERVER=
PROTOCOL=http
DOMAIN=localhost:3000
ENVIRONMENT=
DEVELOPER=

ACCESS_TOKEN_LIFETIME=
REFRESH_TOKEN_LIFETIME=

DB_ENGINE_EX=django.db.backends.postgresql
DB_ENGINE=django.contrib.gis.db.backends.postgis
POSTGRES_DB=yume_db
POSTGRES_USER=
POSTGRES_PASSWORD=
DB_HOST=localhost
DB_PORT=5432

DB_FILE=db.sqlite3

SITE_NAME=yumesushi.rs
EMAIL_HOST=smtp.gmail.com
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_PORT=587

GOOGLE_API_KEY=
SENTRY_DSN=

BOT_TOKEN=
ADMIN_ID=
CHAT_ID=

CONSOLE_LOG_LEVEL=DEBUG
FILE_LOG_LEVEL=DEBUG
API_LOG_LEVEL=DEBUG
CATALOG_LOG_LEVEL=DEBUG
DELIVERY_LOG_LEVEL=DEBUG
PROMOS_LOG_LEVEL=DEBUG
SHOP_LOG_LEVEL=DEBUG
TM_BOT_LOG_LEVEL=DEBUG
USERS_LOG_LEVEL=DEBUG
SESSION_COOKIE_AGE=21600
```

##### Установка пакетов
Для запуска проекта необходимо установить все сторонние пакеты, описанные в requirements.txt.
Находясь в папке с requirements.txt ввести
```
python -m pip install -r requirements.txt
```
##### Создание или внесение изменений в базу данных
При запущенной PostgreSQL 14 и созданной базе данных yume_db,
перейти в корневую папку проекта web_shop_with_bots (уровень файла manage.py), сделать миграции и загрузит дами данные.
```
python manage.py makemigrations - создание макета изменений
python manage.py migrate - применение изменений
python manage.py load_all - загрузить пресеты в базу данных
```

#### Запуск проекта
Находясь в папке web_shop_with_bots
```
python manage.py runserver - запуск проекта
```
БЭКЭНД ЗАПУЩЕН и доступен по адресу http://127.0.0.1:8000/admin/

##### Дополнительные пакеты и команды для справки (установятся автоматически из requirements.txt )
```
pip install django-debug-toolbar==3.2.4  - тулбар для дебага (кол-во запросов)
pip install django-summernote  - редактор HTML
pip install django-filter  - django фильтры
python -m pip freeze > requirements.txt - сохранение пакетов в requirements.txt
```



## Бэкапы Базы данных
#### Настройка бэкапа
В папку infra/ кладется файл backup.sh с настройками команды для добавления в cron на хосте.

```
BACKUP_DIR="/backups"           # путь к директории в контейнере бд, где будут храниться бэкапы
TIMESTAMP=$(date + "%d-%m-%Y")   # метка времени для имени файла
BACKUP_FILE="$BACKUP_DIR/db_backups_$TIMESTAMP.dump"
POSTGRES_CONTAINER=""           # имя контейнера PostgreSQL (замените на фактическое имя)
DB_NAME=""                      # название бд PostgreSQL (замените на фактическое имя)
DB_USER=""                      # имя пользователя PostgreSQL (замените на фактическое имя)
COMPOSE_FILE="/home/YUME_SUSHI/docker-compose.test_server_cache_crontab.yml"  # путь к вашему docker-compose файлу

# Выполнение pg_dump в контейнере PostgreSQL
docker compose -f $COMPOSE_FILE exec $POSTGRES_CONTAINER 'pg_dump -U $DB_USER -d $DB_NAME -F c -b -v -f $BACKUP_FILE'
```

В процесс Cron на хосте добавляются задачи
```
crontab -e
```
добавить
```
0 0 * * * /home/YUME_SUSHI/infra/backup.sh >> /home/YUME_SUSHI/backups/logfile.log 2>&1
```
Каждую полночь будет запускаться скрипт /root/YUME_SUSHI/infra/backup.sh.
Логи, включая ошибки, будут писаться в /root/YUME_SUSHI/backups/logfile.log


#### Восстановление из бэкапа

Для восстановления данных кинуть файл в контейнер с бэкэндом ( в папку самого проекта) и оттуда вызвать команду
(заменив соответствующие перееменные).
Применять к любой бд (пустой/заполненной). Если в бд будут записи, они удалятся.
```
pg_restore --clean -U username -d database_name db_backup_27-05-2024.dump
```


## Очистка базы данных и логов
#### Настройка бэкапа
В папку infra/ кладется файл backup.sh с настройками команды для добавления в cron на хосте.

```
python manage.py delete_expired_tokens      # едаляет истекшие токены blacklist + outstanding
```

В процесс Cron на хосте добавляются задачи
```
crontab -e
```
добавить
```
0 0 * * * docker compose -f /home/YUME_SUSHI/docker-compose.test_server_cache_crontab.yml exec backend python manage.py delete_expired_tokens >> /home/YUME_SUSHI/logging/cronlogfile.log 2>&1
```
Каждую полночь будет в контейнере backend будет вызываться команда delete_expired_tokens.
Логи, включая ошибки, будут писаться в /nome/YUME_SUSHI/logging/cronlogfile.log



## Настройка frontend
#### загрузка

ключи ssh c репой фронтэндера
git clone ssh://git@github.com/Pustovna/sushi-shop-sb.git

npm install
npm install i18next-locize-backend
npm install crypto-js
npm run build


.env
REACT_APP_GOOGLE_API_KEY=''
REACT_APP_URL_DB='yumesushi.rs/'



HTTPS
sudo apt install snapd


- email/
нужны для темплейтов от конкретного сервера, т.к. ссылка на лого для писем для всех серверов разная и не подтягивается через env
