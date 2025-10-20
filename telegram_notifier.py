"""Telegram notification service"""

import os
import logging
from telegram import Bot
from telegram.error import TelegramError
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.bot = None

        if self.bot_token and self.chat_id:
            try:
                self.bot = Bot(token=self.bot_token)
                logger.info("Telegram bot initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Telegram bot: {str(e)}")
        else:
            logger.warning("Telegram credentials not configured")

    def send_message(self, message):
        """Send message to Telegram channel"""
        if not self.bot or not self.chat_id:
            logger.warning("Telegram not configured, skipping notification")
            return False

        try:
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            logger.info("Telegram notification sent successfully")
            return True

        except TelegramError as e:
            logger.error(f"Telegram error: {str(e)}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error sending Telegram message: {str(e)}")
            return False

    def send_ban_notification(self, domain):
        """Send notification when domain gets banned"""
        message = f"""🚨 <b>ДОМЕН ЗАБАНЕН</b>

<b>Домен:</b> {domain.domain}
<b>Проект:</b> {domain.project or 'Не указан'}
<b>Назначение:</b> {domain.purpose or 'Не указано'}
<b>Время проверки:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

⚠️ Google Safe Browsing обнаружил угрозу на этом домене."""

        return self.send_message(message)

    def send_unban_notification(self, domain):
        """Send notification when domain gets unbanned"""
        message = f"""✅ <b>ДОМЕН РАЗБАНЕН</b>

<b>Домен:</b> {domain.domain}
<b>Проект:</b> {domain.project or 'Не указан'}
<b>Назначение:</b> {domain.purpose or 'Не указано'}
<b>Время проверки:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

✨ Домен больше не находится в черном списке Google."""

        return self.send_message(message)

    def send_test_message(self):
        """Send test message to verify configuration"""
        message = """🔔 <b>GDBChecker - Тестовое сообщение</b>

Бот успешно подключен к каналу!
Уведомления о банах доменов будут приходить сюда."""

        return self.send_message(message)


if __name__ == '__main__':
    # Test notification
    notifier = TelegramNotifier()
    if notifier.send_test_message():
        print("Test notification sent successfully!")
    else:
        print("Failed to send test notification. Check your configuration.")
