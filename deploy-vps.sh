#!/bin/bash
#
# Masha OSINT - Automated VPS Deployment Script
# Usage: Run this script on your VPS as root
#
# curl -fsSL https://raw.githubusercontent.com/freire19/Masha-OSINT/main/deploy-vps.sh | bash
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================================"
echo " 🕵️‍♀️  Masha OSINT - VPS Deployment Script"
echo "============================================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: Please run as root${NC}"
    exit 1
fi

# Get domain from user
read -p "Enter your domain (e.g., masha.freirecorporation.com): " DOMAIN
read -p "Enter your email for SSL certificate: " EMAIL

echo -e "${YELLOW}[1/8] Updating system...${NC}"
apt update && apt upgrade -y
apt install -y ufw fail2ban git curl wget vim htop python3 python3-pip python3-venv python3-dev
apt install -y nginx certbot python3-certbot-nginx
apt install -y build-essential libssl-dev libffi-dev libxml2-dev libxslt1-dev

echo -e "${GREEN}✅ System updated${NC}"

echo -e "${YELLOW}[2/8] Configuring firewall (UFW)...${NC}"
ufw --force enable
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw status verbose

echo -e "${GREEN}✅ Firewall configured${NC}"

echo -e "${YELLOW}[3/8] Configuring Fail2Ban...${NC}"
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3
EOF

systemctl enable fail2ban
systemctl restart fail2ban

echo -e "${GREEN}✅ Fail2Ban configured${NC}"

echo -e "${YELLOW}[4/8] Creating masha user...${NC}"
if ! id -u masha > /dev/null 2>&1; then
    useradd -m -s /bin/bash masha
    usermod -aG sudo masha
    echo "masha:$(openssl rand -base64 12)" | chpasswd

    # Copy SSH keys if they exist
    if [ -d /root/.ssh ]; then
        mkdir -p /home/masha/.ssh
        cp /root/.ssh/authorized_keys /home/masha/.ssh/ 2>/dev/null || true
        chown -R masha:masha /home/masha/.ssh
        chmod 700 /home/masha/.ssh
        chmod 600 /home/masha/.ssh/authorized_keys 2>/dev/null || true
    fi

    echo -e "${GREEN}✅ User masha created${NC}"
else
    echo -e "${YELLOW}User masha already exists${NC}"
fi

echo -e "${YELLOW}[5/8] Setting up application...${NC}"
sudo -u masha bash << 'MASHA_SETUP'
set -e

# Create application directory
sudo mkdir -p /opt/masha-osint
sudo chown masha:masha /opt/masha-osint
cd /opt/masha-osint

# Clone repository
if [ ! -d ".git" ]; then
    git clone https://github.com/freire19/Masha-OSINT.git .
else
    git pull origin main
fi

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Copy .env template
if [ ! -f ".env" ]; then
    cp .env.example .env
    chmod 600 .env
    echo "⚠️  IMPORTANT: Edit /opt/masha-osint/.env and add your API keys!"
fi

echo "✅ Application installed"
MASHA_SETUP

echo -e "${GREEN}✅ Application installed${NC}"

echo -e "${YELLOW}[6/8] Creating systemd service...${NC}"
cat > /etc/systemd/system/masha-osint.service << 'EOF'
[Unit]
Description=Masha OSINT - Streamlit Web UI
Documentation=https://github.com/freire19/Masha-OSINT
After=network.target

[Service]
Type=simple
User=masha
Group=masha
WorkingDirectory=/opt/masha-osint

Environment="PATH=/opt/masha-osint/venv/bin"
EnvironmentFile=/opt/masha-osint/.env

ExecStart=/opt/masha-osint/venv/bin/streamlit run app.py \
    --server.port=8501 \
    --server.address=127.0.0.1 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=true \
    --browser.gatherUsageStats=false

Restart=always
RestartSec=10
StartLimitBurst=5
StartLimitInterval=60

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/masha-osint/logs /opt/masha-osint/data
CapabilityBoundingSet=

StandardOutput=journal
StandardError=journal
SyslogIdentifier=masha-osint

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable masha-osint

echo -e "${GREEN}✅ Systemd service created${NC}"

echo -e "${YELLOW}[7/8] Configuring Nginx...${NC}"
cat > /etc/nginx/sites-available/masha-osint << EOF
upstream streamlit_backend {
    server 127.0.0.1:8501 fail_timeout=0;
}

server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN};

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        proxy_pass http://streamlit_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_buffering off;
    }
}
EOF

ln -sf /etc/nginx/sites-available/masha-osint /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl reload nginx

echo -e "${GREEN}✅ Nginx configured${NC}"

echo -e "${YELLOW}[8/8] Obtaining SSL certificate...${NC}"
certbot --nginx -d ${DOMAIN} --non-interactive --agree-tos --email ${EMAIL} || {
    echo -e "${RED}SSL certificate failed. You can run manually later:${NC}"
    echo "sudo certbot --nginx -d ${DOMAIN}"
}

# Update Nginx config with HTTPS redirect
cat > /etc/nginx/sites-available/masha-osint << EOF
upstream streamlit_backend {
    server 127.0.0.1:8501 fail_timeout=0;
}

server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN};

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ${DOMAIN};

    ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;

    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    access_log /var/log/nginx/masha_access.log;
    error_log /var/log/nginx/masha_error.log warn;

    proxy_read_timeout 300s;
    proxy_connect_timeout 75s;

    location / {
        proxy_pass http://streamlit_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_buffering off;
        proxy_cache off;
    }

    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF

nginx -t && systemctl reload nginx

echo -e "${GREEN}✅ SSL configured${NC}"

echo ""
echo "============================================================"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo "============================================================"
echo ""
echo "Next steps:"
echo "1. Edit /opt/masha-osint/.env and add your API keys:"
echo "   sudo nano /opt/masha-osint/.env"
echo ""
echo "2. Start the service:"
echo "   sudo systemctl start masha-osint"
echo ""
echo "3. Check status:"
echo "   sudo systemctl status masha-osint"
echo ""
echo "4. Access your site:"
echo "   https://${DOMAIN}"
echo ""
echo "5. View logs:"
echo "   sudo journalctl -u masha-osint -f"
echo ""
echo "============================================================"
