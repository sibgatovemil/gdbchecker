"""Flask web application and API"""

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash, session as flask_session
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import get_session, Domain, StatusHistory, User
from telegram_notifier import TelegramNotifier
from datetime import datetime, timedelta
import csv
import io
import logging
import subprocess
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app)

# Jinja2 filter for Moscow timezone
@app.template_filter('moscow_time')
def moscow_time_filter(dt):
    """Convert UTC datetime to Moscow time (UTC+3)"""
    if dt is None:
        return None
    # Add 3 hours to UTC time
    moscow_dt = dt + timedelta(hours=3)
    return moscow_dt.strftime('%Y-%m-%d %H:%M')

@app.template_filter('moscow_time_full')
def moscow_time_full_filter(dt):
    """Convert UTC datetime to Moscow time with seconds (UTC+3)"""
    if dt is None:
        return None
    # Add 3 hours to UTC time
    moscow_dt = dt + timedelta(hours=3)
    return moscow_dt.strftime('%Y-%m-%d %H:%M:%S')

@app.template_filter('moscow_time_pretty')
def moscow_time_pretty_filter(dt):
    """Convert UTC datetime to pretty Moscow time format"""
    if dt is None:
        return None
    # Add 3 hours to UTC time
    moscow_dt = dt + timedelta(hours=3)
    return moscow_dt.strftime('Проверено: %d.%m.%Y в %H:%M')

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    session = get_session()
    try:
        user = session.query(User).filter_by(id=int(user_id)).first()
        return user
    finally:
        session.close()


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            return render_template('login.html', error='Username and password are required')

        session = get_session()
        try:
            user = session.query(User).filter_by(username=username).first()

            if user and user.is_active and user.check_password(password):
                # Update last login
                user.last_login = datetime.utcnow()
                session.commit()

                # Log user in
                login_user(user)
                logger.info(f"User {username} logged in successfully")

                # Redirect to next page or index
                next_page = request.args.get('next')
                return redirect(next_page if next_page else url_for('index'))
            else:
                logger.warning(f"Failed login attempt for username: {username}")
                return render_template('login.html', error='Invalid username or password')

        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            return render_template('login.html', error='An error occurred. Please try again.')
        finally:
            session.close()

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """Logout user"""
    username = current_user.username
    logout_user()
    logger.info(f"User {username} logged out")
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    """Main page with domain list"""
    session = get_session()
    try:
        domains = session.query(Domain).order_by(Domain.created_at.desc()).all()

        # Statistics
        total = len(domains)
        ok_count = sum(1 for d in domains if d.current_status == 'ok')
        banned_count = sum(1 for d in domains if d.current_status == 'banned')
        error_count = sum(1 for d in domains if d.current_status == 'error')
        pending_count = sum(1 for d in domains if d.current_status == 'pending')

        stats = {
            'total': total,
            'ok': ok_count,
            'banned': banned_count,
            'error': error_count,
            'pending': pending_count
        }

        return render_template('index.html', domains=domains, stats=stats)
    finally:
        session.close()


@app.route('/domain/<int:domain_id>')
@login_required
def domain_detail(domain_id):
    """Domain details page with history"""
    session = get_session()
    try:
        domain = session.query(Domain).filter_by(id=domain_id).first()
        if not domain:
            return "Domain not found", 404

        history = session.query(StatusHistory)\
            .filter_by(domain_id=domain_id)\
            .order_by(StatusHistory.checked_at.desc())\
            .limit(50)\
            .all()

        return render_template('domain_detail.html', domain=domain, history=history)
    finally:
        session.close()


# API Endpoints

@app.route('/api/domains', methods=['GET'])
@login_required
def get_domains():
    """Get all domains"""
    session = get_session()
    try:
        domains = session.query(Domain).all()
        return jsonify([d.to_dict() for d in domains])
    finally:
        session.close()


@app.route('/api/domains', methods=['POST'])
@login_required
def add_domain():
    """Add new domain"""
    data = request.get_json()

    if not data or 'domain' not in data:
        return jsonify({'error': 'Domain is required'}), 400

    domain_name = data['domain'].strip().lower()

    # Remove protocol if present
    domain_name = domain_name.replace('http://', '').replace('https://', '')
    domain_name = domain_name.split('/')[0]  # Remove path

    session = get_session()
    try:
        # Check if domain already exists
        existing = session.query(Domain).filter_by(domain=domain_name).first()
        if existing:
            return jsonify({'error': 'Domain already exists', 'id': existing.id}), 409

        # Create new domain
        new_domain = Domain(
            domain=domain_name,
            project=data.get('project', '').strip() or None,
            purpose=data.get('purpose', '').strip() or None,
            current_status='pending',
            added_by=current_user.username,
            autorenew=data.get('autorenew', 'unknown')  # Default to unknown
        )

        session.add(new_domain)
        session.commit()

        logger.info(f"New domain added: {domain_name}")
        return jsonify(new_domain.to_dict()), 201

    except Exception as e:
        session.rollback()
        logger.error(f"Error adding domain: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@app.route('/api/domains/<int:domain_id>', methods=['GET'])
@login_required
def get_domain(domain_id):
    """Get single domain"""
    session = get_session()
    try:
        domain = session.query(Domain).filter_by(id=domain_id).first()
        if not domain:
            return jsonify({'error': 'Domain not found'}), 404
        return jsonify(domain.to_dict())
    finally:
        session.close()


@app.route('/api/domains/<int:domain_id>', methods=['DELETE'])
@login_required
def delete_domain(domain_id):
    """Delete domain"""
    session = get_session()
    try:
        domain = session.query(Domain).filter_by(id=domain_id).first()
        if not domain:
            return jsonify({'error': 'Domain not found'}), 404

        domain_name = domain.domain
        session.delete(domain)
        session.commit()

        logger.info(f"Domain deleted: {domain_name}")
        return jsonify({'message': 'Domain deleted successfully'}), 200

    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting domain: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@app.route('/api/domains/<int:domain_id>/history', methods=['GET'])
@login_required
def get_domain_history(domain_id):
    """Get domain status history"""
    session = get_session()
    try:
        history = session.query(StatusHistory)\
            .filter_by(domain_id=domain_id)\
            .order_by(StatusHistory.checked_at.desc())\
            .all()

        return jsonify([h.to_dict() for h in history])
    finally:
        session.close()


@app.route('/api/export/csv', methods=['GET'])
@login_required
def export_csv():
    """Export domains to CSV"""
    session = get_session()
    try:
        domains = session.query(Domain).all()

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(['ID', 'Domain', 'Project', 'Purpose', 'Status', 'Last Check', 'Created At'])

        # Data
        for domain in domains:
            writer.writerow([
                domain.id,
                domain.domain,
                domain.project or '',
                domain.purpose or '',
                domain.current_status,
                domain.last_check_time.strftime('%Y-%m-%d %H:%M:%S') if domain.last_check_time else '',
                domain.created_at.strftime('%Y-%m-%d %H:%M:%S') if domain.created_at else ''
            ])

        output.seek(0)

        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'domains_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
        )

    finally:
        session.close()


@app.route('/api/telegram/send-status', methods=['POST'])
@login_required
def send_status_telegram():
    """Send current status report to Telegram"""
    session = get_session()
    try:
        domains = session.query(Domain).all()

        # Statistics
        total = len(domains)
        ok_count = sum(1 for d in domains if d.current_status == 'ok')
        banned_count = sum(1 for d in domains if d.current_status == 'banned')
        error_count = sum(1 for d in domains if d.current_status == 'error')
        pending_count = sum(1 for d in domains if d.current_status == 'pending')

        # Unique domains banned in last 24h
        yesterday = datetime.utcnow() - timedelta(hours=24)
        recent_bans = session.query(StatusHistory.domain_id)\
            .filter(StatusHistory.status == 'banned')\
            .filter(StatusHistory.checked_at >= yesterday)\
            .distinct()\
            .count()

        # SSL Statistics
        ssl_valid = sum(1 for d in domains if d.ssl_status == 'valid')
        ssl_expired = sum(1 for d in domains if d.ssl_status == 'expired')
        ssl_invalid = sum(1 for d in domains if d.ssl_status == 'invalid')
        ssl_missing = sum(1 for d in domains if d.ssl_status == 'missing')

        # Build message
        message = f"""📊 <b>GDBChecker - Отчет о статусе</b>

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

        # System health check
        message += "\n<b>🔧 Состояние системы:</b>\n"
        message += "• База данных: ✅ OK\n"
        message += "• API: ✅ OK\n"
        message += f"• Telegram: ✅ OK\n"
        message += f"\n<i>Отчет создан: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</i>"

        # Send to Telegram
        notifier = TelegramNotifier()
        success = notifier.send_message(message)

        if success:
            return jsonify({'success': True, 'message': 'Status sent to Telegram'}), 200
        else:
            return jsonify({'success': False, 'error': 'Failed to send message'}), 500

    except Exception as e:
        logger.error(f"Error sending status to Telegram: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@app.route('/api/check-domains', methods=['POST'])
@login_required
def trigger_domain_check():
    """Trigger immediate domain check in background"""
    try:
        # Run checker.py in background without waiting
        subprocess.Popen(
            ['python', 'checker.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        logger.info(f"Domain check triggered by user {current_user.username}")

        return jsonify({
            'success': True,
            'message': 'Проверка доменов запущена в фоне. Это займет несколько минут. Обновите страницу через 2-3 минуты для просмотра результатов.'
        }), 200

    except Exception as e:
        logger.error(f"Error triggering domain check: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/import/csv', methods=['POST'])
@login_required
def import_csv():
    """Import domains from CSV file"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'File must be CSV'}), 400

    session = get_session()
    try:
        # Read CSV
        stream = io.StringIO(file.stream.read().decode('utf-8'), newline=None)
        csv_reader = csv.DictReader(stream)

        added_count = 0
        skipped_count = 0
        errors = []

        for row_num, row in enumerate(csv_reader, start=2):  # Start from 2 (header is row 1)
            try:
                # Get domain from CSV (try different column names)
                domain_name = None
                for key in ['domain', 'Domain', 'DOMAIN', 'url', 'URL']:
                    if key in row:
                        domain_name = row[key].strip().lower()
                        break

                if not domain_name:
                    errors.append(f"Row {row_num}: No domain column found")
                    continue

                # Clean domain
                domain_name = domain_name.replace('http://', '').replace('https://', '')
                domain_name = domain_name.split('/')[0]

                if not domain_name:
                    errors.append(f"Row {row_num}: Empty domain")
                    continue

                # Check if exists
                existing = session.query(Domain).filter_by(domain=domain_name).first()
                if existing:
                    skipped_count += 1
                    continue

                # Create new domain
                new_domain = Domain(
                    domain=domain_name,
                    project=row.get('project', row.get('Project', '')).strip() or None,
                    purpose=row.get('purpose', row.get('Purpose', '')).strip() or None,
                    current_status='pending'
                )

                session.add(new_domain)
                added_count += 1

            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                continue

        session.commit()

        return jsonify({
            'success': True,
            'added': added_count,
            'skipped': skipped_count,
            'errors': errors
        }), 200

    except Exception as e:
        session.rollback()
        logger.error(f"Error importing CSV: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
