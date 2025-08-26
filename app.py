import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///fail2ban_monitor.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

# Import models and services after app creation
from models import BannedIP
from fail2ban_service import Fail2banService

# Initialize scheduler
scheduler = BackgroundScheduler()
fail2ban_service = Fail2banService()

def update_banned_ips():
    """Background task to update banned IPs from Fail2ban"""
    try:
        with app.app_context():
            logger.info("Starting banned IP update task")
            
            # Get current banned IPs from Fail2ban
            current_banned_ips = fail2ban_service.get_banned_ips()
            logger.info(f"Found {len(current_banned_ips)} currently banned IPs")
            
            # Clean up old entries (older than 1 week)
            one_week_ago = datetime.utcnow() - timedelta(weeks=1)
            old_ips = BannedIP.query.filter(BannedIP.banned_at < one_week_ago).all()
            for old_ip in old_ips:
                db.session.delete(old_ip)
            logger.info(f"Cleaned up {len(old_ips)} old IP entries")
            
            # Add new IPs or update existing ones
            updated_count = 0
            for ip_data in current_banned_ips:
                ip_address = ip_data['ip']
                jail = ip_data['jail']
                
                existing_ip = BannedIP.query.filter_by(ip_address=ip_address, jail=jail).first()
                if not existing_ip:
                    new_banned_ip = BannedIP(
                        ip_address=ip_address,
                        jail=jail,
                        banned_at=datetime.utcnow()
                    )
                    db.session.add(new_banned_ip)
                    updated_count += 1
                else:
                    # Update the timestamp to keep it fresh
                    existing_ip.banned_at = datetime.utcnow()
                    updated_count += 1
            
            db.session.commit()
            logger.info(f"Updated {updated_count} IP entries")
            
    except Exception as e:
        logger.error(f"Error updating banned IPs: {str(e)}")

@app.route('/')
def index():
    """Main page displaying banned IPs"""
    try:
        # Get all current banned IPs from database
        banned_ips = BannedIP.query.order_by(BannedIP.banned_at.desc()).all()
        
        # Get last update time (most recent entry)
        last_update = None
        if banned_ips:
            last_update = banned_ips[0].banned_at
        
        # Get Fail2ban service status
        service_status = fail2ban_service.get_service_status()
        
        return render_template('index.html', 
                             banned_ips=banned_ips, 
                             last_update=last_update,
                             service_status=service_status)
    except Exception as e:
        logger.error(f"Error loading index page: {str(e)}")
        return render_template('index.html', 
                             banned_ips=[], 
                             last_update=None,
                             service_status={'running': False, 'error': str(e)})

@app.route('/api/banned-ips')
def api_banned_ips():
    """API endpoint to get banned IPs as JSON"""
    try:
        banned_ips = BannedIP.query.order_by(BannedIP.banned_at.desc()).all()
        
        ips_data = []
        for ip in banned_ips:
            ips_data.append({
                'ip_address': ip.ip_address,
                'jail': ip.jail,
                'banned_at': ip.banned_at.isoformat(),
                'abuse_url': f"https://abuseipdb.com/check/{ip.ip_address}"
            })
        
        return jsonify({
            'success': True,
            'data': ips_data,
            'count': len(ips_data)
        })
    except Exception as e:
        logger.error(f"Error in API endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/refresh')
def api_refresh():
    """API endpoint to manually trigger banned IP refresh"""
    try:
        update_banned_ips()
        return jsonify({
            'success': True,
            'message': 'Banned IPs refreshed successfully'
        })
    except Exception as e:
        logger.error(f"Error refreshing banned IPs: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Initialize database and start scheduler
with app.app_context():
    db.create_all()
    
    # Run initial update
    update_banned_ips()
    
    # Schedule hourly updates
    scheduler.add_job(
        func=update_banned_ips,
        trigger=IntervalTrigger(hours=1),
        id='update_banned_ips',
        name='Update banned IPs from Fail2ban',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler started - banned IPs will update hourly")

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
