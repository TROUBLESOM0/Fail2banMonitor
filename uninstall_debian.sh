#!/bin/bash
#
# Fail2ban Banned IPs Monitor - Debian Uninstallation Script
# Version: v1.0.1
# Description: Automated uninstallation script for Debian/Ubuntu systems
# Date: August 2025
#

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

# Remove sudoers configuration and fail2ban-monitor user
echo "Removing sudo permissions and fail2ban-monitor user..."
if [ -f /etc/sudoers.d/fail2ban-monitor ]; then
    sudo rm /etc/sudoers.d/fail2ban-monitor
fi

# Remove fail2ban-monitor user
if id "fail2ban-monitor" &>/dev/null; then
    sudo userdel fail2ban-monitor
    echo "Removed fail2ban-monitor user"
else
    echo "User fail2ban-monitor does not exist"
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
read -p "Do you want to remove system packages that were installed? (postgresql, python3-pip, python3-venv) (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Removing system packages..."
    sudo apt remove --purge -y postgresql postgresql-contrib python3-pip python3-venv
    sudo apt autoremove -y
    echo "System packages removed."
else
    echo "System packages kept."
fi

# Ask about removing bulk packages
echo
echo "Also, a whole bunch of these others get installed on most systems:::"
echo " (build-essential cpp dpkg-dev fakeroot g++ g++-12 gcc javascript-common libalgorithm-diff-perl libalgorithm-diff-xs-perl libalgorithm-merge-perl libdpkg-perl libexpat1-dev libfakeroot libfile-fcntllock-perl libjs-jquery libjs-sphinxdoc libjs-underscore libjson-perl libllvm14 libpq5 libpython3-dev libpython3.11 libpython3.11-dev libsensors-config libsensors5 libstdc++-12-dev libxslt1.1 libz3-4 make postgresql postgresql-15 postgresql-client-15 postgresql-client-common postgresql-common postgresql-contrib python3-dev python3-distutils python3-lib2to3 python3-pip python3-pip-whl python3-setuptools python3-setuptools-whl python3-venv python3-wheel python3.11-dev python3.11-venv ssl-cert sysstat zlib1g-dev)"
read -p "Do you want to remove these: (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Removing system packages..."
    sudo apt remove --purge -y build-essential cpp dpkg-dev fakeroot g++ g++-12 gcc javascript-common libalgorithm-diff-perl libalgorithm-diff-xs-perl libalgorithm-merge-perl libdpkg-perl libexpat1-dev libfakeroot libfile-fcntllock-perl libjs-jquery libjs-sphinxdoc libjs-underscore libjson-perl libllvm14 libpq5 libpython3-dev libpython3.11 libpython3.11-dev libsensors-config libsensors5 libstdc++-12-dev libxslt1.1 libz3-4 make postgresql postgresql-15 postgresql-client-15 postgresql-client-common postgresql-common postgresql-contrib python3-dev python3-distutils python3-lib2to3 python3-pip python3-pip-whl python3-setuptools python3-setuptools-whl python3-venv python3-wheel python3.11-dev python3.11-venv ssl-cert sysstat zlib1g-dev
    sudo apt autoremove -y
    echo "Bulk packages removed."
else
    echo "Bulk packages kept."
fi

# Ask about removing nginx
echo
read -p "Do you want to remove nginx? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Stopping and removing nginx..."
    sudo systemctl stop nginx
    sudo apt remove --purge -y nginx
    echo "Nginx removed."
else
    echo "Nginx kept."
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
echo "- fail2ban-monitor system user"
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
