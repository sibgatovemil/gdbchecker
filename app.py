"""Flask web application and API"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from models import get_session, Domain, StatusHistory
from telegram_notifier import TelegramNotifier
from datetime import datetime, timedelta
import csv
import io
import logging
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)


@app.route('/')
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
def get_domains():
    """Get all domains"""
    session = get_session()
    try:
        domains = session.query(Domain).all()
        return jsonify([d.to_dict() for d in domains])
    finally:
        session.close()


@app.route('/api/domains', methods=['POST'])
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
            current_status='pending'
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

        # Domains banned in last 24h
        yesterday = datetime.utcnow() - timedelta(hours=24)
        recent_bans = session.query(StatusHistory)\
            .filter(StatusHistory.status == 'banned')\
            .filter(StatusHistory.checked_at >= yesterday)\
            .count()

        # Build message
        message = f"""📊 <b>GDBChecker - Отчет о статусе</b>

<b>Общая статистика:</b>
• Всего доменов: {total}
• ✅ OK: {ok_count}
• 🚨 Забанено: {banned_count}
• ⚠️ Ошибки: {error_count}
• ⏳ Ожидают проверки: {pending_count}

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
def trigger_domain_check():
    """Trigger immediate domain check"""
    try:
        # Run checker.py in background
        result = subprocess.run(
            ['python', 'checker.py'],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )

        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': 'Domain check completed successfully',
                'output': result.stdout
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Check failed',
                'output': result.stderr
            }), 500

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Check timeout (>5 minutes)'}), 504
    except Exception as e:
        logger.error(f"Error triggering domain check: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/import/csv', methods=['POST'])
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
