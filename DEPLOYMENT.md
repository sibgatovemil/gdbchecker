# Инструкция по развертыванию GDBChecker

## Данные для развертывания

**Сервер:**
- IP: 5.223.77.236
- User: root
- SSH Key: ssh_key.pub

**Учетные данные:**
- Google API Key: AIzaSyCbtVAfxF89vL1SypaPMgBrOmuAt-G2o7E
- Telegram Bot Token: 7839039906:AAFOVJPsCq1zI4psDz93RQ5tFrxhwJoLM9c
- Telegram Chat ID: -1002999204995

## Шаг 1: Подключение к серверу

```bash
ssh root@5.223.77.236
```

## Шаг 2: Подготовка проекта на локальной машине

На вашем компьютере (Windows):

```bash
# Перейдите в директорию проекта
cd C:\VSProjects\GDBChecker

# Инициализируйте git репозиторий (если еще не создан)
git init
git add .
git commit -m "Initial commit"
```

## Шаг 3: Копирование файлов на сервер

### Вариант А: Через SCP (рекомендуется)

```bash
# Создайте архив проекта
cd C:\VSProjects
tar -czf gdbchecker.tar.gz GDBChecker/

# Скопируйте на сервер
scp gdbchecker.tar.gz root@5.223.77.236:/tmp/
```

### Вариант Б: Вручную

1. Создайте zip архив папки GDBChecker
2. Используйте WinSCP или FileZilla для загрузки на сервер

## Шаг 4: Установка на сервере

```bash
# Подключитесь к серверу
ssh root@5.223.77.236

# Распакуйте архив
cd /opt
tar -xzf /tmp/gdbchecker.tar.gz
mv GDBChecker gdbchecker
cd gdbchecker

# Создайте .env файл
cat > .env << 'EOF'
# Database
DB_PASSWORD=GDBSecurePass2025!

# Google Safe Browsing API
GOOGLE_API_KEY=AIzaSyCbtVAfxF89vL1SypaPMgBrOmuAt-G2o7E

# Telegram
TELEGRAM_BOT_TOKEN=7839039906:AAFOVJPsCq1zI4psDz93RQ5tFrxhwJoLM9c
TELEGRAM_CHAT_ID=-1002999204995

# Checker settings
CHECK_INTERVAL_HOURS=8
EOF

# Сделайте скрипт установки исполняемым
chmod +x deploy.sh

# Запустите установку
./deploy.sh
```

## Шаг 5: Проверка работы

```bash
# Проверьте статус контейнеров
docker compose ps

# Должны работать 2 контейнера:
# - gdbchecker_db (PostgreSQL)
# - gdbchecker_web (Python приложение)

# Проверьте логи
docker compose logs -f web

# Нажмите Ctrl+C для выхода из просмотра логов
```

## Шаг 6: Тестирование

### Проверка веб-интерфейса

Откройте в браузере: http://5.223.77.236:8080

### Тест Telegram уведомлений

```bash
docker compose exec web python telegram_notifier.py
```

Вы должны получить тестовое сообщение в Telegram канале.

### Добавление тестового домена

Через веб-интерфейс или API:

```bash
curl -X POST http://5.223.77.236:8080/api/domains \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "test.com",
    "project": "Test Project",
    "purpose": "Testing"
  }'
```

### Ручной запуск проверки

```bash
docker compose exec web python checker.py
```

## Шаг 7: Настройка firewall (опционально)

```bash
# Установите UFW
apt-get install -y ufw

# Разрешите SSH
ufw allow 22/tcp

# Разрешите порт приложения
ufw allow 8080/tcp

# Включите firewall
ufw enable
```

## Полезные команды

### Просмотр логов

```bash
# Все логи
docker compose logs -f

# Только веб-приложение
docker compose logs -f web

# Только база данных
docker compose logs -f db
```

### Перезапуск

```bash
# Перезапуск всех сервисов
docker compose restart

# Перезапуск только веб-приложения
docker compose restart web
```

### Остановка

```bash
docker compose down
```

### Обновление

```bash
cd /opt/gdbchecker
git pull  # если используете git
docker compose up -d --build
```

### Резервное копирование базы данных

```bash
# Создание бэкапа
docker compose exec db pg_dump -U gdbchecker gdbchecker > backup_$(date +%Y%m%d).sql

# Восстановление из бэкапа
docker compose exec -T db psql -U gdbchecker gdbchecker < backup_20250101.sql
```

## Решение проблем

### Порт 8080 уже занят

```bash
# Проверьте, что занимает порт
netstat -tulpn | grep 8080

# Измените порт в docker-compose.yml
nano docker-compose.yml
# Измените "8080:8080" на "8081:8080"

# Перезапустите
docker compose up -d
```

### Контейнеры не запускаются

```bash
# Проверьте логи
docker compose logs

# Пересоздайте контейнеры
docker compose down
docker compose up -d --build
```

### Ошибки подключения к базе данных

```bash
# Проверьте, что БД работает
docker compose exec db psql -U gdbchecker -c "SELECT 1;"

# Пересоздайте volume БД (ВНИМАНИЕ: удалит все данные!)
docker compose down -v
docker compose up -d
```

## Мониторинг

### Проверка использования ресурсов

```bash
# CPU и память контейнеров
docker stats

# Место на диске
df -h

# Размер логов Docker
du -sh /var/lib/docker/containers/*/*-json.log
```

### Настройка автозапуска

Docker Compose уже настроен на автозапуск (`restart: always`).
Контейнеры будут автоматически перезапускаться при перезагрузке сервера.

## Безопасность

1. **Смените пароль БД** в .env на более надежный
2. **Ограничьте доступ к серверу**: используйте только SSH ключи
3. **Настройте HTTPS**: установите nginx + certbot для SSL
4. **Регулярные обновления**:
```bash
apt-get update && apt-get upgrade -y
```

## Поддержка

При возникновении проблем проверьте:
1. Логи: `docker compose logs -f`
2. Статус: `docker compose ps`
3. Доступность API: `curl http://localhost:8080/health`
4. Конфигурацию: `cat .env`
