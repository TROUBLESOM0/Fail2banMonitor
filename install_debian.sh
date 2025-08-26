#!/bin/bash

# Fail2ban Monitor Installation Script for Debian Linux
# This script installs and configures the Fail2ban Monitor application

set -e  # Exit on any error

echo "=== Fail2ban Monitor Installation Script for Debian ==="
echo "This script will install and configure the Fail2ban Monitor application"
echo

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "Please do not run this script as root. Run as a regular user with sudo privileges."
   exit 1
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

# Create dedicated fail2ban-monitor user (no home directory)
echo "Creating fail2ban-monitor user..."
if ! id "fail2ban-monitor" &>/dev/null; then
    sudo useradd -r -s /bin/false fail2ban-monitor
    echo "Created fail2ban-monitor user (system account, no home directory)"
else
    echo "User fail2ban-monitor already exists"
fi

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
    server_name localhost;  # Change to your domain name

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static {
        alias $APP_DIR/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
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
echo "fail2ban-monitor ALL=(ALL) NOPASSWD: /usr/bin/fail2ban-client, /usr/local/bin/fail2ban-client" | sudo tee /etc/sudoers.d/fail2ban-monitor
sudo chmod 440 /etc/sudoers.d/fail2ban-monitor

echo
echo "=== Installation Complete ==="
echo
echo "Next steps:"
echo "1. Copy your application files to: $APP_DIR"
echo "   sudo cp -r /path/to/your/app/* $APP_DIR/"
echo "   sudo chown -R fail2ban-monitor:fail2ban-monitor $APP_DIR"
echo "2. Make sure the following files are present:"
echo "   - app.py"
echo "   - main.py"
echo "   - templates/ directory"
echo "   - static/ directory"
echo
echo "3. Start the service:"
echo "   sudo systemctl enable fail2ban-monitor"
echo "   sudo systemctl start fail2ban-monitor"
echo
echo "4. Check service status:"
echo "   sudo systemctl status fail2ban-monitor"
echo
echo "5. View application logs:"
echo "   sudo journalctl -u fail2ban-monitor -f"
echo
echo "6. Access the application at: http://your-server-ip"
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