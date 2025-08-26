import os
import logging
import atexit
from datetime import datetime, timedelta
from flask import render_template, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from database import create_app, db
from model_loader import get_model

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create the Flask application
app = create_app()

# Initialize scheduler
scheduler = BackgroundScheduler()

def update_banned_ips():
    """Background task to update banned IPs from Fail2ban"""
    try:
        with app.app_context():
            # Import services and get models
            from fail2ban_service import Fail2banService
            
            # Get the model using model loader
            BannedIP = get_model('BannedIP')
            
            fail2ban_service = Fail2banService()
            logger.info("Starting banned IP update task")
            
            # Get current banned IPs from Fail2ban
            current_ips = fail2ban_service.get_banned_ips()
            logger.info(f"Found {len(current_ips)} currently banned IPs")
            
            # Clear existing records and add current ones
            BannedIP.query.delete()
            
            for ip_info in current_ips:
                banned_ip = BannedIP(
                    ip_address=ip_info['ip'],
                    jail=ip_info['jail'],
                    banned_at=datetime.utcnow()
                )
                db.session.add(banned_ip)
            
            # Clean up old entries (older than 1 week)
            one_week_ago = datetime.utcnow() - timedelta(weeks=1)
            old_count = BannedIP.query.filter(BannedIP.banned_at < one_week_ago).count()
            BannedIP.query.filter(BannedIP.banned_at < one_week_ago).delete()
            logger.info(f"Cleaned up {old_count} old IP entries")
            
            db.session.commit()
            
            # Log results
            total_count = BannedIP.query.count()
            logger.info(f"Updated {total_count} IP entries")
            
    except Exception as e:
        logger.error(f"Error updating banned IPs: {str(e)}")
        if 'db' in locals():
            db.session.rollback()

@app.route('/')
def index():
    """Main dashboard page"""
    try:
        # Import services and get models
        from fail2ban_service import Fail2banService
        
        # Get the model using model loader
        BannedIP = get_model('BannedIP')
        
        fail2ban_service = Fail2banService()
        
        # Get all current banned IPs from database
        banned_ips = BannedIP.query.order_by(BannedIP.banned_at.desc()).all()
        
        # Get Fail2ban service status
        service_status = fail2ban_service.get_service_status()
        
        # Get jail information
        jails = fail2ban_service.get_jails()
        
        # Calculate statistics
        total_banned = len(banned_ips)
        unique_jails = len(set(ip.jail for ip in banned_ips)) if banned_ips else 0
        
        # Group IPs by jail for statistics
        jail_stats = {}
        for ip in banned_ips:
            if ip.jail in jail_stats:
                jail_stats[ip.jail] += 1
            else:
                jail_stats[ip.jail] = 1
        
        return render_template('index.html',
                             banned_ips=banned_ips,
                             service_status=service_status,
                             jails=jails,
                             total_banned=total_banned,
                             unique_jails=unique_jails,
                             jail_stats=jail_stats)
    except Exception as e:
        logger.error(f"Error loading index page: {str(e)}")
        return render_template('index.html',
                             banned_ips=[],
                             service_status={'running': False, 'error': str(e)},
                             jails=[],
                             total_banned=0,
                             unique_jails=0,
                             jail_stats={})

@app.route('/api/banned-ips')
def api_banned_ips():
    """API endpoint to get banned IPs as JSON"""
    try:
        # Get the model using model loader
        BannedIP = get_model('BannedIP')
        
        banned_ips = BannedIP.query.order_by(BannedIP.banned_at.desc()).all()
        
        ips_data = []
        for ip in banned_ips:
            ips_data.append({
                'id': ip.id,
                'ip_address': ip.ip_address,
                'jail': ip.jail,
                'banned_at': ip.banned_at.isoformat(),
                'abuse_url': f"https://abuseipdb.com/check/{ip.ip_address}"
            })
        
        return jsonify({
            'success': True,
            'data': ips_data,
            'total': len(ips_data)
        })
    except Exception as e:
        logger.error(f"Error in API endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': [],
            'total': 0
        }), 500

@app.route('/api/refresh')
def api_refresh():
    """API endpoint to manually trigger IP list refresh"""
    try:
        update_banned_ips()
        return jsonify({'success': True, 'message': 'IP list refreshed successfully'})
    except Exception as e:
        logger.error(f"Error refreshing IP list: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Initialize the application
if __name__ != '__main__':
    # This runs when imported by Gunicorn
    with app.app_context():
        try:
            # Load models using model loader
            BannedIP = get_model('BannedIP')
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
        except Exception as e:
            logger.error(f"Error during app initialization: {str(e)}")

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown() if scheduler.running else None)

if __name__ == '__main__':
    # This runs when running directly (not via Gunicorn)
    with app.app_context():
        BannedIP = get_model('BannedIP')
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
    
    app.run(host='0.0.0.0', port=5000, debug=True)