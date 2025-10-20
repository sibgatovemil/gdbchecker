"""Domain checker service using Google Safe Browsing API"""

import requests
import os
import json
from datetime import datetime
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
                    status, details = self.check_domain(domain.domain)
                    old_status = domain.current_status

                    # Update domain status
                    domain.current_status = status
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

        except Exception as e:
            logger.error(f"Error in check_all_domains: {str(e)}")
            session.rollback()

        finally:
            session.close()


if __name__ == '__main__':
    checker = DomainChecker()
    checker.check_all_domains()
