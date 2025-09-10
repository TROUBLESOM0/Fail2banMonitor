#!/bin/bash
#
# Fail2ban Banned IPs Monitor - Debian Installation Script
# Version: v2.0.3
# Description: Automated installation script for Debian/Ubuntu systems
# Date: August 2025
#

# Fail2ban Monitor Installation Script for Debian Linux
# This script installs and configures the Fail2ban Monitor application

set -e  # Exit on any error
_pwd=`dirname "$(realpath $0)"`

echo "=== Fail2ban Monitor Installation Script for Debian ==="
echo "This script will install and configure the Fail2ban Monitor application"
echo

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "Please do not run this script as root. Run as a regular user with sudo privileges."
   exit 1
fi

# Verify Debian version
if [[ -f /etc/os-release ]]
then :
else
echo "++Unable to get OS Version from os-release++"
echo -e "++Will continue but may have compatibility issues++\n"
fi

os_version=$(cat /etc/os-release | grep VERSION_CODENAME | cut -d '=' -f2)
if [[ $os_version = "buster" ]]
then echo -e "OS Version: Buster (compatible)\n"
elif [[ $os_version = "bullseye" ]]
then echo -e "OS Version: Bullseye (compatible)\n"
elif [[ $os_version = "bookworm" ]]
then echo -e "OS Version: Bookworm (compatible)\n"
elif [[ $os_version = "" ]]
then echo "OS Version (not-found): $os_version (non-compatible)"
echo -e "Will continue installation, but may be issues\n"
#exit 1
else echo -e "OS Version: $os_version may not be compatible, but will continue installation\n"
#exit 1
fi

# Confirm installation
read -p "Do You Want To Proceed With Installation (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[yY]$ ]]; then
    echo "Installation cancelled."
    exit 0
fi

# Update system packages
echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required system packages
echo "Installing system dependencies..."
sudo apt install -y python3 python3-pip python3-venv fail2ban nginx postgresql postgresql-contrib

# Check if Fail2ban is installed and running
echo "Checking Fail2ban installation..."
if ! command -v fail2ban-client &> /dev/null; then
    echo "Error: fail2ban-client not found. Installing fail2ban..."
    sudo apt install -y fail2ban
fi

# Start and enable Fail2ban service
echo "Starting Fail2ban service..."
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Verify Fail2ban is running
if ! sudo systemctl is-active --quiet fail2ban; then
    echo "Warning: Fail2ban service is not running. Please check the configuration."
else
    echo "Fail2ban service is running successfully."
fi

# Check fail2ban version requirement
echo "Checking fail2ban version..."
fb_version=$(sudo fail2ban-client -V 2>&1 | grep -oP '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "0.0.0")
required_version="0.11.1"

# Function to compare version strings
version_compare() {
    local ver1=$1
    local ver2=$2
    
    IFS='.' read -ra VER1 <<< "$ver1"
    IFS='.' read -ra VER2 <<< "$ver2"
    
    # Compare major, minor, patch
    for i in {0..2}; do
        local num1=${VER1[i]:-0}
        local num2=${VER2[i]:-0}
        
        if (( num1 > num2 )); then
            return 0  # ver1 > ver2
        elif (( num1 < num2 )); then
            return 1  # ver1 < ver2
        fi
    done
    
    return 0  # versions are equal
}

if version_compare "$fb_version" "$required_version"; then
    echo "Fail2ban version $fb_version meets minimum requirement ($required_version)"
else
    echo "Error: Fail2ban version $fb_version is below minimum requirement ($required_version)"
    echo "Please update fail2ban to version $required_version or higher before continuing."
    echo "You can try: sudo apt update && sudo apt install fail2ban"
    echo "Or download v1.0.0 (https://github.com/TROUBLESOM0/Fail2banMonitor/archive/refs/tags/v1.0.0.zip)"
    exit 1
fi

# Create dedicated fail2ban-monitor user (no home directory)
echo "Creating fail2ban-monitor user..."
if ! id "fail2ban-monitor" &>/dev/null; then
    sudo useradd -r -s /bin/bash fail2ban-monitor
    echo "Created fail2ban-monitor user (system account, no home directory)"
else
    echo "User fail2ban-monitor already exists"
fi

# Add fail2ban-monitor user to necessary groups
echo "Adding fail2ban-monitor to system groups..."
sudo usermod -a -G adm fail2ban-monitor 2>/dev/null || true
sudo usermod -a -G systemd-journal fail2ban-monitor 2>/dev/null || true

# Create application directory
APP_DIR="/opt/fail2ban-monitor"
echo "Creating application directory at $APP_DIR..."
sudo mkdir -p $APP_DIR
sudo chown fail2ban-monitor:fail2ban-monitor $APP_DIR

# Create Python virtual environment as fail2ban-monitor user
echo "Creating Python virtual environment..."
sudo -u fail2ban-monitor python3 -m venv $APP_DIR/venv

# Install Python dependencies
echo "Installing Python dependencies..."
sudo -u fail2ban-monitor $APP_DIR/venv/bin/pip install --upgrade pip
sudo -u fail2ban-monitor $APP_DIR/venv/bin/pip install Flask==2.3.3
sudo -u fail2ban-monitor $APP_DIR/venv/bin/pip install gunicorn==21.2.0
sudo -u fail2ban-monitor $APP_DIR/venv/bin/pip install APScheduler==3.10.4
sudo -u fail2ban-monitor $APP_DIR/venv/bin/pip install Werkzeug==2.3.7
sudo -u fail2ban-monitor $APP_DIR/venv/bin/pip install email-validator==2.0.0

# Copy application files (assuming they're in the current directory)
echo "Please copy your application files to $APP_DIR"
echo "Required files: app.py, main.py, models.py, fail2ban_service.py, templates/, static/"
echo

# Create environment file
echo "Creating environment configuration..."
sudo -u fail2ban-monitor tee $APP_DIR/.env > /dev/null << EOF
SESSION_SECRET=$(openssl rand -hex 32)
EOF

# Create systemd service file
echo "Creating systemd service..."
sudo tee /etc/systemd/system/fail2ban-monitor.service > /dev/null << EOF
[Unit]
Description=Fail2ban Monitor Web Application
After=network.target fail2ban.service
Wants=fail2ban.service

[Service]
Type=exec
User=fail2ban-monitor
Group=fail2ban-monitor
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 2 main:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Configure Nginx reverse proxy
echo "Configuring Nginx reverse proxy..."
sudo tee /etc/nginx/sites-available/fail2ban-monitor > /dev/null << EOF
server {
    listen 80;
    listen 443 ssl http2;
    server_name localhost;
#    include /etc/nginx/certs/ssl.conf;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static {
        alias $APP_DIR/static;
    #    expires 1y;  #cache header for 1yr
    #    add_header Cache-Control "public, immutable";  #allow CDN's cache until expires
    }
}
EOF

# Enable Nginx site
sudo ln -sf /etc/nginx/sites-available/fail2ban-monitor /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx

# Set up fail2ban permissions for the application user
echo "Configuring fail2ban permissions..."
cat << 'EOF' | sudo tee /etc/sudoers.d/fail2ban-monitor
Defaults:fail2ban-monitor !requiretty
Defaults:fail2ban-monitor env_keep += "PATH"
fail2ban-monitor ALL=(ALL) NOPASSWD: /usr/bin/fail2ban-client
fail2ban-monitor ALL=(ALL) NOPASSWD: /usr/local/bin/fail2ban-client
EOF
sudo chmod 440 /etc/sudoers.d/fail2ban-monitor

echo
echo "=== Installation Complete ==="
echo
echo "Copying application files to: $APP_DIR"
sudo cp -r $_pwd/* $APP_DIR/
sudo chown -R fail2ban-monitor:fail2ban-monitor $APP_DIR
echo 
echo "Make sure the following files are present:"
echo "   - app.py"
echo "   - main.py"
echo "   - templates/ directory"
echo "   - static/ directory"
echo
echo "Starting the service:"
sudo systemctl enable fail2ban-monitor
sudo systemctl start fail2ban-monitor
echo
echo " Check service status with:"
echo "   sudo systemctl status fail2ban-monitor"
echo
echo " View application logs with:"
echo "   sudo journalctl -u fail2ban-monitor -f"
echo
echo " Access the application at: http://your-server-ip"
echo
echo "Configuration files created:"
echo "- Application directory: $APP_DIR"
echo "- Environment file: $APP_DIR/.env"
echo "- Systemd service: /etc/systemd/system/fail2ban-monitor.service"
echo "- Nginx config: /etc/nginx/sites-available/fail2ban-monitor"
echo
echo "Security Features:"
echo "- Dedicated fail2ban-monitor user (no shell, no home directory)"
echo "- Limited sudo access only to /usr/bin/fail2ban-client"
echo "- Application runs with minimal privileges"
