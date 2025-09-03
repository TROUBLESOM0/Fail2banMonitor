#!/usr/bin/env python3
"""
Fail2ban Banned IPs Monitor - Main Application
Version: v2.0.0
Description: Flask web application for monitoring and displaying banned IPs from Fail2ban
Author: Fail2ban Monitor System
Date: August 2025
"""

import os
import json
import logging
import subprocess
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit
import pytz

# Application version
APP_VERSION = "v2.0.0"
APP_NAME = "Fail2ban Banned IPs Monitor"

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize scheduler
scheduler = BackgroundScheduler()

# File to store banned IPs
BANNED_IPS_FILE = "banned_ips.json"

def get_jail_color(jail_name):
    """Return Bootstrap badge color class based on jail name"""
    jail_colors = {
        'sshd': 'bg-danger',        # Red for SSH attacks
        'apache': 'bg-warning',     # Yellow for Apache attacks  
        'nginx': 'bg-info',         # Blue for Nginx attacks
        'postfix': 'bg-success',    # Green for mail attacks
        'dovecot': 'bg-primary',    # Primary blue for IMAP/POP3
        'vsftpd': 'bg-secondary',   # Gray for FTP attacks
        'proftpd': 'bg-secondary',  # Gray for FTP attacks
        'pure-ftpd': 'bg-secondary', # Gray for FTP attacks
        'asterisk': 'bg-dark',      # Dark for VoIP attacks
        'roundcube': 'bg-warning',  # Yellow for webmail
        'wordpress': 'bg-info',     # Blue for WordPress
        'drupal': 'bg-info',        # Blue for Drupal
        'joomla': 'bg-info',        # Blue for Joomla
        'phpmyadmin': 'bg-danger',  # Red for database admin
        'mysqld': 'bg-danger',      # Red for database
        'postgresql': 'bg-danger',  # Red for database
        'suhosin': 'bg-warning',    # Yellow for PHP security
        'recidive': 'bg-dark',      # Dark for repeat offenders
    }
    
    # Default to secondary (gray) for unknown jails
    return jail_colors.get(jail_name.lower(), 'bg-secondary')

# Register the function as a template function
app.jinja_env.globals.update(get_jail_color=get_jail_color)

def get_banned_ips_from_fail2ban():
    """Get banned IPs from fail2ban using the specified command"""
    try:
        # Try with sudo first (production), then without sudo (development)
        commands_to_try = [
            ["sudo", "/usr/bin/fail2ban-client", "get", "sshd", "banip"],
            ["/usr/bin/fail2ban-client", "get", "sshd", "banip"],
            ["sudo", "fail2ban-client", "get", "sshd", "banip"],
            ["fail2ban-client", "get", "sshd", "banip"]
        ]
        
        for cmd in commands_to_try:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    env={'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'}
                )
                
                if result.returncode == 0:
                    # Parse the output - split by spaces and filter out empty strings
                    ips = [ip.strip() for ip in result.stdout.split() if ip.strip()]
                    return ips
                else:
                    logger.debug(f"Command {' '.join(cmd)} returned error code {result.returncode}: {result.stderr}")
            except FileNotFoundError:
                logger.debug(f"Command not found: {' '.join(cmd)}")
                continue
        
        logger.warning("fail2ban-client not found or not accessible. Is Fail2ban installed?")
        return []
    except subprocess.TimeoutExpired:
        logger.error("fail2ban-client command timed out")
        return []
    except Exception as e:
        logger.error(f"Error getting banned IPs: {str(e)}")
        return []

def get_all_jails():
    """Get list of all fail2ban jails"""
    try:
        # Try with sudo first (production), then without sudo (development)
        commands_to_try = [
            ["sudo", "/usr/bin/fail2ban-client", "status"],
            ["/usr/bin/fail2ban-client", "status"],
            ["sudo", "fail2ban-client", "status"],
            ["fail2ban-client", "status"]
        ]
        
        for cmd in commands_to_try:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    env={'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'}
                )
                
                if result.returncode == 0:
                    # Parse jail names from status output
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'Jail list:' in line:
                            jails_part = line.split('Jail list:')[1].strip()
                            jails = [jail.strip() for jail in jails_part.split(',') if jail.strip()]
                            return jails
                    return ["sshd"]  # Default to sshd if parsing fails
                else:
                    logger.debug(f"Command {' '.join(cmd)} returned error code {result.returncode}: {result.stderr}")
            except FileNotFoundError:
                logger.debug(f"Command not found: {' '.join(cmd)}")
                continue
        
        logger.warning("fail2ban-client not found or not accessible. Using default jails.")
        return ["sshd"]  # Default to sshd if fail2ban-client not available
    except Exception as e:
        logger.error(f"Error getting jails: {str(e)}")
        return ["sshd"]

def get_banned_ips_for_jail(jail):
    """Get banned IPs for a specific jail"""
    try:
        # Try with sudo first (production), then without sudo (development)
        commands_to_try = [
            ["sudo", "/usr/bin/fail2ban-client", "get", jail, "banip"],
            ["/usr/bin/fail2ban-client", "get", jail, "banip"],
            ["sudo", "fail2ban-client", "get", jail, "banip"],
            ["fail2ban-client", "get", jail, "banip"]
        ]
        
        for cmd in commands_to_try:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    env={'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'}
                )
                
                if result.returncode == 0:
                    ips = [ip.strip() for ip in result.stdout.split() if ip.strip()]
                    return ips
                else:
                    logger.debug(f"Command {' '.join(cmd)} returned error code {result.returncode}: {result.stderr}")
            except FileNotFoundError:
                logger.debug(f"Command not found: {' '.join(cmd)}")
                continue
        
        return []
    except Exception as e:
        logger.error(f"Error getting banned IPs for jail {jail}: {str(e)}")
        return []

def load_banned_ips_from_file():
    """Load banned IPs from JSON file"""
    try:
        if os.path.exists(BANNED_IPS_FILE):
            with open(BANNED_IPS_FILE, 'r') as f:
                data = json.load(f)
                return data
        return {"ips": [], "last_updated": None}
    except Exception as e:
        logger.error(f"Error loading banned IPs from file: {str(e)}")
        return {"ips": [], "last_updated": None}

def save_banned_ips_to_file(ips_data):
    """Save banned IPs to JSON file"""
    try:
        with open(BANNED_IPS_FILE, 'w') as f:
            json.dump(ips_data, f, indent=2)
        logger.info(f"Saved {len(ips_data['ips'])} banned IPs to file")
    except Exception as e:
        logger.error(f"Error saving banned IPs to file: {str(e)}")

def update_banned_ips():
    """Update banned IPs from all fail2ban jails"""
    try:
        logger.info("Starting banned IP update task")
        
        # Get all jails
        jails = get_all_jails()
        logger.info(f"Found jails: {jails}")
        
        all_ips = []
        # Get current time for tracking updates (Central Time)
        central_tz = pytz.timezone('America/Chicago')
        current_time = datetime.now(central_tz)
        
        # Get actual ban times for all currently banned IPs
        actual_ban_times = get_banned_ips_with_actual_ban_times()
        
        # Get banned IPs from each jail
        for jail in jails:
            jail_ips = get_banned_ips_for_jail(jail)
            for ip in jail_ips:
                # Try to get the actual ban time, fallback to current time if not available
                ip_jail_key = f"{ip}_{jail}"
                actual_ban_time = actual_ban_times.get(ip_jail_key, current_time.isoformat())
                
                ip_record = {
                    "ip_address": ip,
                    "jail": jail,
                    "banned_at": actual_ban_time,
                    "abuse_url": f"https://abuseipdb.com/check/{ip}"
                }
                all_ips.append(ip_record)
        
        # Load existing data
        existing_data = load_banned_ips_from_file()
        
        # Clean up old entries (older than 1 week)
        one_week_ago = current_time - timedelta(weeks=1)
        cleaned_ips = []
        
        for ip_record in existing_data.get("ips", []):
            try:
                banned_time = datetime.fromisoformat(ip_record["banned_at"])
                if banned_time > one_week_ago:
                    cleaned_ips.append(ip_record)
            except:
                # Keep records with invalid dates
                cleaned_ips.append(ip_record)
        
        # Merge current IPs with existing ones (avoid duplicates)
        existing_ip_keys = set()
        for ip_record in cleaned_ips:
            key = f"{ip_record['ip_address']}_{ip_record['jail']}"
            existing_ip_keys.add(key)
        
        # Add new IPs that aren't already tracked
        for ip_record in all_ips:
            key = f"{ip_record['ip_address']}_{ip_record['jail']}"
            if key not in existing_ip_keys:
                cleaned_ips.append(ip_record)
        
        # Save updated data
        updated_data = {
            "ips": cleaned_ips,
            "last_updated": current_time.isoformat()
        }
        
        save_banned_ips_to_file(updated_data)
        logger.info(f"Updated banned IPs: {len(all_ips)} currently banned, {len(cleaned_ips)} total tracked")
        
    except Exception as e:
        logger.error(f"Error updating banned IPs: {str(e)}")

def get_banned_ips_with_actual_ban_times():
    """Get banned IPs with their actual ban start times from fail2ban"""
    try:
        # Get all available jails first
        all_jails = get_all_jails()
        if not all_jails:
            all_jails = ['sshd']  # Default fallback
        
        ban_data = {}  # Dictionary to store IP -> ban_time mapping
        
        # Check each jail for banned IPs with their actual ban times
        for jail in all_jails:
            try:
                # Use the command to get IP, date, and time of ban start
                cmd = f"sudo fail2ban-client get {jail} banip --with-time | awk '{{print $1, $2, $3}}'"
                
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    env={'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'}
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    lines = result.stdout.strip().split('\n')
                    
                    for line in lines:
                        if line.strip():
                            # The command gives us: IP date time (3 fields separated by spaces)
                            parts = line.strip().split()
                            if len(parts) >= 3:
                                ip = parts[0]
                                ban_date = parts[1]
                                ban_time = parts[2]
                                
                                # Combine date and time for complete timestamp
                                full_datetime_str = f"{ban_date} {ban_time}"
                                formatted_time = datetime.now().isoformat()  # Default fallback
                                
                                try:
                                    # Try to parse as epoch timestamp first
                                    if ban_date.replace('.', '').isdigit():
                                        ban_time_dt = datetime.fromtimestamp(float(ban_date))
                                        formatted_time = ban_time_dt.isoformat()
                                    else:
                                        # Try to parse as date/time string format
                                        try:
                                            # Common formats: YYYY-MM-DD HH:MM:SS or MM/DD/YYYY HH:MM:SS
                                            for fmt in ['%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M:%S', '%Y-%m-%d %H:%M', '%m/%d/%Y %H:%M']:
                                                try:
                                                    parsed_dt = datetime.strptime(full_datetime_str, fmt)
                                                    formatted_time = parsed_dt.isoformat()
                                                    break
                                                except ValueError:
                                                    continue
                                        except:
                                            # If all parsing fails, use current time as fallback
                                            formatted_time = datetime.now().isoformat()
                                except (ValueError, OverflowError, OSError):
                                    # Use current time as fallback
                                    formatted_time = datetime.now().isoformat()
                                
                                # Store the ban time for this IP-jail combination
                                key = f"{ip}_{jail}"
                                ban_data[key] = formatted_time
                                
            except Exception as e:
                logger.debug(f"Error getting actual ban times for jail {jail}: {str(e)}")
                continue
        
        return ban_data
            
    except Exception as e:
        logger.error(f"Error getting banned IPs with actual ban times: {str(e)}")
        return {}

def get_banned_ips_with_times():
    """Get banned IPs with their ban expiration times"""
    try:
        # Get all available jails first
        all_jails = get_all_jails()
        if not all_jails:
            all_jails = ['sshd']  # Default fallback
        
        ban_data = []
        
        # Check each jail for banned IPs with times
        for jail in all_jails:
            try:
                # Use the specific command format provided by the user
                cmd = f"sudo fail2ban-client get {jail} banip --with-time | awk '{{print $1, $7, $8}}'"
                
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    env={'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'}
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    lines = result.stdout.strip().split('\n')
                    
                    for line in lines:
                        if line.strip():
                            # The awk command gives us: IP date time (3 fields separated by spaces)
                            parts = line.strip().split()
                            if len(parts) >= 3:
                                ip = parts[0]
                                ban_date = parts[1]
                                ban_time = parts[2]
                                
                                # Combine date and time for complete timestamp
                                full_datetime_str = f"{ban_date} {ban_time}"
                                formatted_time = full_datetime_str
                                
                                try:
                                    # Try to parse as epoch timestamp first
                                    if ban_date.replace('.', '').isdigit():
                                        ban_time_dt = datetime.fromtimestamp(float(ban_date))
                                        formatted_time = ban_time_dt.strftime('%m/%d/%Y %I:%M:%S %p CST')
                                    else:
                                        # Try to parse as date/time string format and reformat
                                        try:
                                            # Common formats: YYYY-MM-DD HH:MM:SS or MM/DD/YYYY HH:MM:SS
                                            for fmt in ['%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M:%S', '%Y-%m-%d %H:%M', '%m/%d/%Y %H:%M']:
                                                try:
                                                    parsed_dt = datetime.strptime(full_datetime_str, fmt)
                                                    formatted_time = parsed_dt.strftime('%m/%d/%Y %I:%M:%S %p CST')
                                                    break
                                                except ValueError:
                                                    continue
                                        except:
                                            # If all parsing fails, just add CST to the original combined string
                                            formatted_time = f"{full_datetime_str} CST"
                                except (ValueError, OverflowError, OSError):
                                    # Keep original format with CST label
                                    formatted_time = f"{full_datetime_str} CST"
                                
                                ban_data.append({
                                    'ip': ip,
                                    'ban_end_time': formatted_time,
                                    'jail': jail  # Use the current jail we're checking
                                })
                                
            except Exception as e:
                logger.debug(f"Error getting ban times for jail {jail}: {str(e)}")
                continue
        
        return ban_data
            
    except Exception as e:
        logger.error(f"Error getting banned IPs with times: {str(e)}")
        return []

def get_fail2ban_status():
    """Check if fail2ban service is running"""
    try:
        # Try different ways to check service status
        commands_to_try = [
#            ["sudo", "/usr/bin/systemctl", "is-active", "fail2ban"],
            ["/usr/bin/systemctl", "is-active", "fail2ban"],
            ["sudo", "systemctl", "is-active", "fail2ban"],
            ["systemctl", "is-active", "fail2ban"]
        ]
        
        for cmd in commands_to_try:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=5,
                    env={'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'}
                )
                if result.returncode == 0:
                    return {
                        "running": True,
                        "status": result.stdout.strip()
                    }
            except FileNotFoundError:
                logger.debug(f"Command not found: {' '.join(cmd)}")
                continue
        
        return {
            "running": False,
            "status": "fail2ban service not accessible or not installed"
        }
    except Exception as e:
        return {
            "running": False,
            "error": str(e)
        }

@app.route('/')
def index():
    """Main dashboard page"""
    try:
        # Load banned IPs from file
        data = load_banned_ips_from_file()
        banned_ips = data.get("ips", [])
        last_updated = data.get("last_updated")
        
        # Get service status
        service_status = get_fail2ban_status()
        
        # Format last_updated for display in Central Time
        formatted_last_updated = None
        if last_updated:
            try:
                # Parse the ISO format timestamp and convert to Central Time
                if isinstance(last_updated, str):
                    dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                else:
                    dt = last_updated
                
                # Convert to Central Time
                central_tz = pytz.timezone('America/Chicago')
                if dt.tzinfo is None:
                    # Assume UTC if no timezone info
                    dt = pytz.utc.localize(dt)
                dt_central = dt.astimezone(central_tz)
                formatted_last_updated = dt_central.strftime('%m/%d/%Y %I:%M:%S %p CST')
            except Exception as e:
                logger.error(f"Error formatting last_updated time: {e}")
                formatted_last_updated = last_updated
        
        # Calculate statistics
        total_banned = len(banned_ips)
        unique_jails = len(set(ip["jail"] for ip in banned_ips)) if banned_ips else 0
        
        # Group IPs by jail for statistics
        jail_stats = {}
        for ip in banned_ips:
            jail = ip["jail"]
            if jail in jail_stats:
                jail_stats[jail] += 1
            else:
                jail_stats[jail] = 1
        
        # Get list of jails
        jails = get_all_jails()
        
        return render_template('index.html',
                             banned_ips=banned_ips,
                             service_status=service_status,
                             jails=jails,
                             total_banned=total_banned,
                             unique_jails=unique_jails,
                             jail_stats=jail_stats,
                             last_updated=formatted_last_updated)
    except Exception as e:
        logger.error(f"Error loading index page: {str(e)}")
        return render_template('index.html',
                             banned_ips=[],
                             service_status={'running': False, 'error': str(e)},
                             jails=[],
                             total_banned=0,
                             unique_jails=0,
                             jail_stats={},
                             last_updated=None)

@app.route('/ban-times')
def ban_times():
    """Page showing current banned IPs with their ban expiration times"""
    try:
        # Get banned IPs with expiration times
        ban_data = get_banned_ips_with_times()
        
        # Get service status
        service_status = get_fail2ban_status()
        
        return render_template('ban_times.html',
                             ban_data=ban_data,
                             service_status=service_status,
                             total_bans=len(ban_data))
    except Exception as e:
        logger.error(f"Error loading ban times page: {str(e)}")
        return render_template('ban_times.html',
                             ban_data=[],
                             service_status={'running': False, 'error': str(e)},
                             total_bans=0)

@app.route('/api/banned-ips')
def api_banned_ips():
    """API endpoint to get banned IPs as JSON"""
    try:
        data = load_banned_ips_from_file()
        banned_ips = data.get("ips", [])
        
        return jsonify({
            'success': True,
            'data': banned_ips,
            'total': len(banned_ips),
            'last_updated': data.get("last_updated")
        })
    except Exception as e:
        logger.error(f"Error in API endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': [],
            'total': 0
        }), 500

@app.route('/api/version')
def api_version():
    """API endpoint to get application version information"""
    return jsonify({
        'name': APP_NAME,
        'version': APP_VERSION,
        'status': 'running'
    })

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
atexit.register(lambda: scheduler.shutdown() if scheduler.running else None)

if __name__ == '__main__':
    # This runs when running directly (not via Gunicorn)
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
