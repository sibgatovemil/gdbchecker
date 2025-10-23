"""Domain checker service using Google Safe Browsing API"""

import requests
import os
import json
import ssl
import socket
from datetime import datetime, timedelta
from models import get_session, Domain, StatusHistory
from telegram_notifier import TelegramNotifier
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DomainChecker:
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_API_KEY')
        self.api_url = 'https://safebrowsing.googleapis.com/v4/threatMatches:find'
        self.notifier = TelegramNotifier()

    def check_domain(self, domain):
        """
        Check domain using Google Safe Browsing API
        Returns: 'ok', 'banned', or 'error'
        """
        if not self.api_key:
            logger.error("Google API key not configured")
            return 'error', 'API key not configured'

        # Prepare request payload
        payload = {
            "client": {
                "clientId": "gdbchecker",
                "clientVersion": "1.0.0"
            },
            "threatInfo": {
                "threatTypes": [
                    "MALWARE",
                    "SOCIAL_ENGINEERING",
                    "UNWANTED_SOFTWARE",
                    "POTENTIALLY_HARMFUL_APPLICATION"
                ],
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [
                    {"url": f"http://{domain}"},
                    {"url": f"https://{domain}"}
                ]
            }
        }

        try:
            response = requests.post(
                f"{self.api_url}?key={self.api_key}",
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()

                # If matches found - domain is banned
                if 'matches' in result and len(result['matches']) > 0:
                    threat_types = [match.get('threatType', 'UNKNOWN') for match in result['matches']]
                    details = {
                        'threat_types': threat_types,
                        'platform': result['matches'][0].get('platformType', 'UNKNOWN'),
                        'checked_at': datetime.utcnow().isoformat()
                    }
                    return 'banned', json.dumps(details)
                else:
                    # No threats found - domain is OK
                    return 'ok', json.dumps({'checked_at': datetime.utcnow().isoformat()})

            elif response.status_code == 400:
                logger.error(f"Bad request for domain {domain}: {response.text}")
                return 'error', f"Bad request: {response.text}"

            elif response.status_code == 429:
                logger.warning(f"Rate limit exceeded for domain {domain}")
                return 'error', "Rate limit exceeded"

            else:
                logger.error(f"API error {response.status_code} for domain {domain}: {response.text}")
                return 'error', f"API error: {response.status_code}"

        except requests.exceptions.Timeout:
            logger.error(f"Timeout checking domain {domain}")
            return 'error', "Request timeout"

        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception for domain {domain}: {str(e)}")
            return 'error', f"Request failed: {str(e)}"

        except Exception as e:
            logger.error(f"Unexpected error checking domain {domain}: {str(e)}")
            return 'error', f"Unexpected error: {str(e)}"

    def check_ssl(self, domain):
        """
        Check SSL certificate status
        Returns: 'valid', 'expired', 'invalid', 'missing'
        """
        try:
            # Try HTTPS connection
            context = ssl.create_default_context()

            with socket.create_connection((domain, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()

                    # Check if certificate is valid
                    not_after = cert.get('notAfter')
                    if not_after:
                        # Parse expiration date
                        from datetime import datetime
                        expiry_date = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')

                        if expiry_date < datetime.utcnow():
                            return 'expired'

                    # Certificate is valid
                    return 'valid'

        except ssl.SSLError as e:
            # SSL error - invalid or self-signed certificate
            logger.warning(f"SSL error for {domain}: {str(e)}")
            if 'certificate verify failed' in str(e).lower():
                return 'invalid'
            return 'invalid'

        except socket.gaierror:
            # Domain doesn't resolve
            logger.warning(f"Domain {domain} doesn't resolve")
            return 'missing'

        except (socket.timeout, ConnectionRefusedError, OSError):
            # HTTPS not available - try HTTP to check if domain exists
            try:
                response = requests.head(f"http://{domain}", timeout=5, allow_redirects=True)
                # Domain exists but no HTTPS
                return 'missing'
            except:
                # Domain completely unavailable
                return 'missing'

        except Exception as e:
            logger.error(f"Unexpected error checking SSL for {domain}: {str(e)}")
            return 'missing'

    def check_all_domains(self):
        """Check all domains in database"""
        session = get_session()
        logger.info("Starting domain check cycle...")

        try:
            domains = session.query(Domain).all()
            total = len(domains)
            logger.info(f"Found {total} domains to check")

            checked_count = 0
            banned_count = 0
            unbanned_count = 0
            error_count = 0

            for domain in domains:
                try:
                    # Check SafeBrowsing status
                    status, details = self.check_domain(domain.domain)
                    old_status = domain.current_status

                    # Check SSL status
                    ssl_status = self.check_ssl(domain.domain)

                    # Update domain status
                    domain.current_status = status
                    domain.ssl_status = ssl_status
                    domain.last_check_time = datetime.utcnow()

                    # Create history record
                    history = StatusHistory(
                        domain_id=domain.id,
                        status=status,
                        checked_at=datetime.utcnow(),
                        details=details
                    )
                    session.add(history)

                    # Send notifications on status change
                    if old_status != status:
                        if status == 'banned' and old_status != 'banned':
                            # Domain got banned
                            self.notifier.send_ban_notification(domain)
                            banned_count += 1
                            logger.warning(f"Domain BANNED: {domain.domain}")

                        elif status == 'ok' and old_status == 'banned':
                            # Domain got unbanned
                            self.notifier.send_unban_notification(domain)
                            unbanned_count += 1
                            logger.info(f"Domain UNBANNED: {domain.domain}")

                    if status == 'error':
                        error_count += 1

                    checked_count += 1

                    # Commit after each domain to avoid losing progress
                    session.commit()

                except Exception as e:
                    logger.error(f"Error processing domain {domain.domain}: {str(e)}")
                    session.rollback()
                    error_count += 1

            logger.info(f"Check cycle completed: {checked_count}/{total} domains checked, "
                       f"{banned_count} newly banned, {unbanned_count} unbanned, {error_count} errors")

            # Send status report to Telegram after check
            self.send_status_report(session)

        except Exception as e:
            logger.error(f"Error in check_all_domains: {str(e)}")
            session.rollback()

        finally:
            session.close()

    def send_status_report(self, session):
        """Send status report to Telegram"""
        try:
            domains = session.query(Domain).all()
            total = len(domains)
            ok_count = sum(1 for d in domains if d.current_status == 'ok')
            banned_count = sum(1 for d in domains if d.current_status == 'banned')
            error_count = sum(1 for d in domains if d.current_status == 'error')
            pending_count = sum(1 for d in domains if d.current_status == 'pending')

            # SSL Statistics
            ssl_valid = sum(1 for d in domains if d.ssl_status == 'valid')
            ssl_expired = sum(1 for d in domains if d.ssl_status == 'expired')
            ssl_invalid = sum(1 for d in domains if d.ssl_status == 'invalid')
            ssl_missing = sum(1 for d in domains if d.ssl_status == 'missing')

            # Count domains that changed from 'ok' to 'banned' in last 24h
            yesterday = datetime.utcnow() - timedelta(hours=24)
            recent_bans = 0

            # For each domain, check if it was banned in last 24h
            for domain in domains:
                # Get last banned record within 24h
                last_ban = session.query(StatusHistory)\
                    .filter(StatusHistory.domain_id == domain.id)\
                    .filter(StatusHistory.status == 'banned')\
                    .filter(StatusHistory.checked_at >= yesterday)\
                    .order_by(StatusHistory.checked_at.desc())\
                    .first()

                if last_ban:
                    # Check if previous status before this ban was 'ok'
                    previous = session.query(StatusHistory)\
                        .filter(StatusHistory.domain_id == domain.id)\
                        .filter(StatusHistory.checked_at < last_ban.checked_at)\
                        .order_by(StatusHistory.checked_at.desc())\
                        .first()

                    # Count as new ban if previous status was 'ok' or no previous status
                    if not previous or previous.status == 'ok':
                        recent_bans += 1

            # Build message
            message = f"""📊 <b>KiteGroup DMS - Отчет о статусе</b>

<b>SafeBrowsing статистика:</b>
• Всего доменов: {total}
• ✅ OK: {ok_count}
• 🚨 Забанено: {banned_count}
• ⚠️ Ошибки: {error_count}
• ⏳ Ожидают проверки: {pending_count}

<b>🔒 SSL Статус:</b>
• ✅ Валидный SSL: {ssl_valid}
• ⚠️ SSL истёк: {ssl_expired}
• ⚠️ Невалидный SSL: {ssl_invalid}
• ❌ SSL отсутствует: {ssl_missing}

<b>За последние 24 часа:</b>
• Новых банов: {recent_bans}
"""

            # Add banned domains list
            if banned_count > 0:
                banned_domains = [d for d in domains if d.current_status == 'banned']
                message += "\n<b>🚨 Забаненные домены:</b>\n"
                for d in banned_domains[:10]:  # Limit to 10
                    message += f"• {d.domain}"
                    if d.project:
                        message += f" ({d.project})"
                    message += "\n"
                if banned_count > 10:
                    message += f"<i>... и еще {banned_count - 10} доменов</i>\n"

            message += f"\n<i>Отчет создан: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</i>"

            # Send to Telegram
            self.notifier.send_message(message)
            logger.info("Status report sent to Telegram")

        except Exception as e:
            logger.error(f"Error sending status report: {str(e)}")


if __name__ == '__main__':
    checker = DomainChecker()
    checker.check_all_domains()
