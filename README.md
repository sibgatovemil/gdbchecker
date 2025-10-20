# GDBChecker - Domain Ban Monitoring System

Система мониторинга доменов на предмет бана в Google Safe Browsing.

## Возможности

- ✅ Автоматическая проверка доменов через Google Safe Browsing API
- ✅ Уведомления в Telegram при бане/разбане доменов
- ✅ Веб-интерфейс для управления доменами
- ✅ REST API для интеграции
- ✅ История изменений статусов
- ✅ Экспорт данных в CSV
- ✅ Группировка по проектам и назначениям

## Быстрый старт

### Предварительные требования

- Сервер с Ubuntu 24.04
- Google Safe Browsing API ключ
- Telegram бот и канал

### 1. Создание Telegram бота

1. Напишите [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям и сохраните токен бота
4. Создайте канал и добавьте бота как администратора
5. Получите chat_id канала

### 2. Получение Google API ключа

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект
3. Включите Safe Browsing API
4. Создайте API ключ

### 3. Развертывание на сервере

```bash
# Подключитесь к серверу
ssh root@your_server_ip

# Клонируйте репозиторий
cd /opt
git clone <repository_url> gdbchecker
cd gdbchecker

# Создайте .env файл
cp .env.example .env
nano .env

# Отредактируйте .env файл:
# DB_PASSWORD=придумайте_надежный_пароль
# GOOGLE_API_KEY=ваш_ключ_от_google
# TELEGRAM_BOT_TOKEN=токен_вашего_бота
# TELEGRAM_CHAT_ID=id_вашего_канала
# CHECK_INTERVAL_HOURS=8

# Запустите скрипт установки
chmod +x deploy.sh
sudo ./deploy.sh
```

### 4. Доступ к системе

После успешного развертывания:
- Веб-интерфейс: `http://your_server_ip:8080`
- API: `http://your_server_ip:8080/api`

## Использование

### Веб-интерфейс

1. **Добавить домен**: Нажмите "Add Domain", заполните форму
2. **Просмотр доменов**: Главная страница со списком всех доменов
3. **История проверок**: Кликните на домен для просмотра истории
4. **Экспорт**: Кнопка "Export CSV" для выгрузки данных

### API

#### Получить все домены
```bash
GET /api/domains
```

#### Добавить домен
```bash
POST /api/domains
Content-Type: application/json

{
  "domain": "example.com",
  "project": "Project Name",
  "purpose": "Landing"
}
```

#### Удалить домен
```bash
DELETE /api/domains/{id}
```

#### Получить историю домена
```bash
GET /api/domains/{id}/history
```

#### Экспорт в CSV
```bash
GET /api/export/csv
```

## Управление сервисом

### Просмотр логов
```bash
cd /opt/gdbchecker
docker compose logs -f
```

### Перезапуск сервисов
```bash
docker compose restart
```

### Остановка сервисов
```bash
docker compose down
```

### Обновление кода
```bash
git pull
docker compose up -d --build
```

### Ручная проверка доменов
```bash
docker compose exec web python checker.py
```

### Тест Telegram уведомлений
```bash
docker compose exec web python telegram_notifier.py
```

## Структура проекта

```
gdbchecker/
├── app.py                  # Flask веб-приложение
├── checker.py              # Сервис проверки доменов
├── telegram_notifier.py    # Telegram уведомления
├── scheduler.py            # Планировщик задач
├── models.py               # Модели базы данных
├── init_db.py             # Инициализация БД
├── requirements.txt        # Python зависимости
├── Dockerfile             # Docker образ
├── docker-compose.yml     # Docker Compose конфигурация
├── deploy.sh              # Скрипт развертывания
├── .env.example           # Пример конфигурации
└── templates/             # HTML шаблоны
    ├── base.html
    ├── index.html
    └── domain_detail.html
```

## Технологии

- **Backend**: Python, Flask
- **Database**: PostgreSQL
- **Scheduler**: APScheduler
- **API**: Google Safe Browsing API
- **Notifications**: Telegram Bot API
- **Frontend**: Bootstrap 5
- **Deployment**: Docker, Docker Compose

## Настройки

### Интервал проверки

По умолчанию домены проверяются каждые 8 часов. Изменить можно в `.env`:
```
CHECK_INTERVAL_HOURS=8
```

### Лимиты Google API

Google Safe Browsing API бесплатен до 10,000 запросов в день.
С 1000 доменов и проверкой каждые 8 часов = ~3000 запросов/день.

## Безопасность

- **НЕ** коммитьте `.env` файл в репозиторий
- Используйте сильные пароли для базы данных
- Ограничьте доступ к серверу через firewall
- Рассмотрите использование HTTPS (nginx + Let's Encrypt)

## Поддержка

При возникновении проблем проверьте:
1. Логи: `docker compose logs -f`
2. Статус контейнеров: `docker compose ps`
3. Конфигурацию `.env`
4. Доступность Google API и Telegram

## Лицензия

MIT License
