# Создать образ на основе базового слоя,
# который содержит файлы ОС и интерпретатор Python 3.9.
FROM python:3.11

# Переходим в образе в директорию /app: в ней будем хранить код проекта.
# Если директории с указанным именем нет, она будет создана.
# Название директории может быть любым.
WORKDIR /app
# Дальнейшие инструкции будут выполняться в директории /app
RUN pip install gunicorn==20.1.0
RUN apt-get update && apt-get install -y \
    sudo \
    nano

RUN apt-get update && apt-get install -y \
    gdal-bin \
    python3-gdal \
    libgdal-dev

RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN ldconfig

# Скопировать с локального компьютера файл зависимостей
# в текущую директорию (текущая директория — это /app).
COPY ./web_shop_with_bots/requirements.txt .

# Выполнить в текущей директории команду терминала
# для установки зависимостей.
RUN pip install -r requirements.txt --no-cache-dir

# Скопировать всё необходимое содержимое
# той директории локального компьютера, где сохранён Dockerfile,
# в текущую рабочую директорию образа — /app.
COPY . .
WORKDIR /app/web_shop_with_bots

# При старте контейнера запустить сервер разработки.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "web_shop_with_bots.wsgi"]
