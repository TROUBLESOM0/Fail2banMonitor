#!/bin/bash

# Fail2ban Monitor Uninstall Script for Debian Linux
# This script removes the Fail2ban Monitor application and its components

set -e  # Exit on any error

echo "=== Fail2ban Monitor Uninstall Script ==="
echo "This script will remove the Fail2ban Monitor application"
echo

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "Please do not run this script as root. Run as a regular user with sudo privileges."
   exit 1
fi

# Confirm uninstallation
read -p "Are you sure you want to uninstall Fail2ban Monitor? This will remove all application files and configurations. (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Uninstallation cancelled."
    exit 0
fi

APP_DIR="/opt/fail2ban-monitor"

echo "Starting uninstallation process..."

# Stop and disable the systemd service
echo "Stopping and disabling fail2ban-monitor service..."
if sudo systemctl is-active --quiet fail2ban-monitor; then
    sudo systemctl stop fail2ban-monitor
fi

if sudo systemctl is-enabled --quiet fail2ban-monitor; then
    sudo systemctl disable fail2ban-monitor
fi

# Remove systemd service file
echo "Removing systemd service file..."
if [ -f /etc/systemd/system/fail2ban-monitor.service ]; then
    sudo rm /etc/systemd/system/fail2ban-monitor.service
    sudo systemctl daemon-reload
fi

# Remove Nginx configuration
echo "Removing Nginx configuration..."
if [ -f /etc/nginx/sites-enabled/fail2ban-monitor ]; then
    sudo rm /etc/nginx/sites-enabled/fail2ban-monitor
fi

if [ -f /etc/nginx/sites-available/fail2ban-monitor ]; then
    sudo rm /etc/nginx/sites-available/fail2ban-monitor
fi

# Test and reload Nginx configuration
if sudo nginx -t 2>/dev/null; then
    sudo systemctl reload nginx
else
    echo "Warning: Nginx configuration test failed. Please check Nginx manually."
fi

# Remove sudoers configuration
echo "Removing sudo permissions..."
if [ -f /etc/sudoers.d/fail2ban-monitor ]; then
    sudo rm /etc/sudoers.d/fail2ban-monitor
fi

# Remove application directory
echo "Removing application directory..."
if [ -d "$APP_DIR" ]; then
    # Backup database if it exists
    if [ -f "$APP_DIR/fail2ban_monitor.db" ]; then
        echo "Backing up database to /tmp/fail2ban_monitor_backup.db..."
        cp "$APP_DIR/fail2ban_monitor.db" /tmp/fail2ban_monitor_backup.db
    fi
    
    sudo rm -rf "$APP_DIR"
fi

# Remove user from adm group (only if they were added by our installer)
echo "Note: User remains in 'adm' group as it may be needed for other applications."
echo "If you want to remove from 'adm' group manually, run:"
echo "sudo gpasswd -d $USER adm"

# Ask about removing system packages
echo
read -p "Do you want to remove system packages that were installed? (nginx, postgresql, python3-pip, python3-venv) (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Removing system packages..."
    sudo apt remove --purge -y nginx postgresql postgresql-contrib python3-pip python3-venv
    sudo apt autoremove -y
    echo "System packages removed."
else
    echo "System packages kept (recommended if used by other applications)."
fi

# Ask about removing Fail2ban
echo
read -p "Do you want to remove Fail2ban? WARNING: This will stop all IP blocking! (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Stopping and removing Fail2ban..."
    sudo systemctl stop fail2ban
    sudo systemctl disable fail2ban
    sudo apt remove --purge -y fail2ban
    echo "Fail2ban removed. Your server is no longer protected by Fail2ban!"
else
    echo "Fail2ban kept running for continued protection."
fi

echo
echo "=== Uninstallation Complete ==="
echo
echo "Removed:"
echo "- Fail2ban Monitor application directory: $APP_DIR"
echo "- Systemd service: fail2ban-monitor"
echo "- Nginx configuration: fail2ban-monitor"
echo "- Sudo permissions for fail2ban-client"
echo
echo "Preserved:"
echo "- Database backup (if existed): /tmp/fail2ban_monitor_backup.db"
echo "- User group memberships"
echo "- System packages (unless you chose to remove them)"
echo "- Fail2ban service (unless you chose to remove it)"
echo
echo "If you want to reinstall later, you can:"
echo "1. Run the install_debian.sh script again"
echo "2. Restore the database from /tmp/fail2ban_monitor_backup.db if needed"
echo
echo "Thank you for using Fail2ban Monitor!"