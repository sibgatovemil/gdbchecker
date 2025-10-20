# Быстрый старт - 5 минут

## На вашем Windows компьютере

### 1. Создайте архив проекта

```powershell
# Откройте PowerShell в папке C:\VSProjects
cd C:\VSProjects

# Создайте zip архив
Compress-Archive -Path .\GDBChecker\* -DestinationPath .\gdbchecker.zip
```

## На сервере (5.223.77.236)

### 2. Подключитесь к серверу

```bash
ssh root@5.223.77.236
```

### 3. Загрузите файлы

После подключения к серверу, на вашем Windows:
- Используйте WinSCP или просто перетащите `gdbchecker.zip` на сервер

Или через PowerShell (если есть scp):
```powershell
scp C:\VSProjects\gdbchecker.zip root@5.223.77.236:/tmp/
```

### 4. На сервере выполните

```bash
# Установите unzip если нужно
apt-get update && apt-get install -y unzip

# Распакуйте проект
cd /opt
unzip /tmp/gdbchecker.zip -d gdbchecker
cd gdbchecker

# Создайте .env файл (одной командой!)
cat > .env << 'EOF'
DB_PASSWORD=GDBSecurePass2025!
GOOGLE_API_KEY=AIzaSyCbtVAfxF89vL1SypaPMgBrOmuAt-G2o7E
TELEGRAM_BOT_TOKEN=7839039906:AAFOVJPsCq1zI4psDz93RQ5tFrxhwJoLM9c
TELEGRAM_CHAT_ID=-1002999204995
CHECK_INTERVAL_HOURS=8
EOF

# Запустите установку (это установит Docker и запустит приложение)
chmod +x deploy.sh
./deploy.sh
```

### 5. Готово!

Откройте в браузере: **http://5.223.77.236:8080**

---

## Проверка работы Telegram

```bash
docker compose exec web python telegram_notifier.py
```

## Добавление доменов

Через веб-интерфейс или API:

```bash
curl -X POST http://5.223.77.236:8080/api/domains \
  -H "Content-Type: application/json" \
  -d '{"domain": "example.com", "project": "Test", "purpose": "Landing"}'
```

## Полезные команды

```bash
# Логи
docker compose logs -f

# Перезапуск
docker compose restart

# Остановка
docker compose down

# Статус
docker compose ps
```
