# Masha OSINT - Production Deployment Guide

Complete guide for deploying Masha-OSINT to a VPS with domain and SSL certificate.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Phase 1: VPS Security Hardening](#phase-1-vps-security-hardening)
- [Phase 2: Application Deployment](#phase-2-application-deployment)
- [Phase 3: Service Configuration](#phase-3-service-configuration)
- [Phase 4: Monitoring & Maintenance](#phase-4-monitoring--maintenance)
- [Troubleshooting](#troubleshooting)

---

## Overview

Masha OSINT v3.0 is deployed using the following stack:

```
Internet → Domain (HTTPS:443)
          ↓
       Nginx (SSL termination, reverse proxy)
          ↓
       Streamlit App (localhost:8501)
          ↓
       Masha OSINT (Python/DeepSeek AI)
```

**Architecture:**
- **Streamlit Web UI** (app.py) on port 8501
- **CLI Tool** (main.py) for command-line operations
- **AI Pipeline**: DeepSeek → SerpAPI → Web Crawler → Sherlock → Analysis
- **No database** required (JSON logging)

---

## Prerequisites

### Infrastructure Requirements
- **VPS**: Ubuntu 22.04+ or Debian 11+ (2GB RAM minimum, 4GB recommended)
- **Domain**: A record pointing to VPS IP
- **Access**: Root or sudo user
- **Ports**: 22 (SSH), 80 (HTTP), 443 (HTTPS)

### API Keys Required
- **DeepSeek API Key** (https://platform.deepseek.com)
- **SerpAPI Key** (https://serpapi.com)
- **RapidAPI Key** (optional, for BreachDirectory)

---

## Phase 1: VPS Security Hardening

### 1.1 Initial Connection

```bash
ssh root@YOUR_VPS_IP
```

### 1.2 System Update

```bash
apt update && apt upgrade -y
apt install -y ufw fail2ban git curl wget vim htop
```

### 1.3 Configure UFW Firewall

```bash
# Allow required ports
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP (Certbot)'
ufw allow 443/tcp comment 'HTTPS'

# Enable firewall
ufw --force enable

# Verify
ufw status verbose
```

**Expected output:**
```
Status: active

To                         Action      From
--                         ------      ----
22/tcp (SSH)              ALLOW       Anywhere
80/tcp (HTTP)             ALLOW       Anywhere
443/tcp (HTTPS)           ALLOW       Anywhere
```

### 1.4 Configure Fail2Ban

Create `/etc/fail2ban/jail.local`:

```bash
sudo tee /etc/fail2ban/jail.local > /dev/null << 'EOF'
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
```

Enable and start:

```bash
systemctl enable fail2ban
systemctl restart fail2ban

# Verify
fail2ban-client status sshd
```

### 1.5 Create Non-Root User

```bash
# Create masha user
useradd -m -s /bin/bash masha
usermod -aG sudo masha

# Set password
passwd masha

# Optional: Copy SSH keys from root
mkdir -p /home/masha/.ssh
cp /root/.ssh/authorized_keys /home/masha/.ssh/ 2>/dev/null || true
chown -R masha:masha /home/masha/.ssh
chmod 700 /home/masha/.ssh
chmod 600 /home/masha/.ssh/authorized_keys 2>/dev/null || true
```

### 1.6 Install System Dependencies

```bash
# Python 3.12+ (or 3.10+ minimum)
apt install -y python3 python3-pip python3-venv python3-dev

# Nginx web server
apt install -y nginx

# Certbot for SSL
apt install -y certbot python3-certbot-nginx

# Build dependencies
apt install -y build-essential libssl-dev libffi-dev libxml2-dev libxslt1-dev

# Verify Python version
python3 --version
```

---

## Phase 2: Application Deployment

### 2.1 Setup Application Directory

```bash
# Switch to masha user
su - masha

# Create application directory
sudo mkdir -p /opt/masha-osint
sudo chown masha:masha /opt/masha-osint
cd /opt/masha-osint
```

### 2.2 Clone Repository

```bash
git clone https://github.com/freire19/Masha-OSINT.git .

# Verify files
ls -la
```

### 2.3 Setup Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

**Expected:** ~50 packages installed (takes 2-3 minutes)

### 2.4 Configure Environment Variables

**CRITICAL SECURITY STEP:**

```bash
# Copy template
cp .env.example .env

# Edit with your API keys
nano .env
```

**Required configuration in .env:**

```bash
# === REQUIRED API KEYS ===
DEEPSEEK_API_KEY=sk-your-actual-deepseek-key-here
SERPAPI_KEY=your-actual-serpapi-key-here

# === WEB UI SECURITY ===
# CHANGE THIS PASSWORD!
MASHA_WEB_PASSWORD=your-secure-password-NOT-12345

# === OPTIONAL ===
RAPIDAPI_KEY=your-rapidapi-key-if-available
DEEPSEEK_MODEL=deepseek-reasoner
MASHA_USE_LOCAL_CNPJ_DB=false
```

**Secure .env permissions:**

```bash
chmod 600 .env
chown masha:masha .env

# Verify (should show: -rw-------)
ls -la .env
```

### 2.5 Verify Installation

```bash
source /opt/masha-osint/venv/bin/activate
cd /opt/masha-osint
python health_check.py
```

**Expected output:** "✅ SISTEMA PRONTO PARA USO"

---

## Phase 3: Service Configuration

### 3.1 Create Systemd Service

Create `/etc/systemd/system/masha-osint.service`:

```bash
sudo tee /etc/systemd/system/masha-osint.service > /dev/null << 'EOF'
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

# Security hardening
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
```

**Enable and start:**

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable on boot
sudo systemctl enable masha-osint

# Start service
sudo systemctl start masha-osint

# Check status
sudo systemctl status masha-osint

# Test locally
curl http://localhost:8501
```

### 3.2 Configure Nginx Reverse Proxy

**Step 1: Create temporary HTTP-only config for Certbot:**

```bash
sudo tee /etc/nginx/sites-available/masha-osint > /dev/null << 'EOF'
upstream streamlit_backend {
    server 127.0.0.1:8501 fail_timeout=0;
}

server {
    listen 80;
    listen [::]:80;
    server_name YOUR_DOMAIN_HERE;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        proxy_pass http://streamlit_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_buffering off;
    }
}
EOF
```

**Replace YOUR_DOMAIN_HERE with your actual domain:**

```bash
sudo sed -i 's/YOUR_DOMAIN_HERE/masha.freirecorporation.com/g' /etc/nginx/sites-available/masha-osint
```

**Enable site:**

```bash
sudo ln -s /etc/nginx/sites-available/masha-osint /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default 2>/dev/null || true

# Test configuration
sudo nginx -t

# Reload
sudo systemctl reload nginx
```

### 3.3 Obtain SSL Certificate

**Verify DNS is pointing to your VPS:**

```bash
dig +short YOUR_DOMAIN
# Should return your VPS IP
```

**Obtain certificate:**

```bash
sudo certbot --nginx -d YOUR_DOMAIN
```

**Certbot prompts:**
- Email: (enter your email)
- Agree to ToS: Y
- Share email: N (optional)

**Certbot will automatically:**
1. Obtain SSL certificate
2. Update Nginx configuration
3. Set up auto-renewal

**Verify auto-renewal:**

```bash
sudo certbot renew --dry-run
systemctl list-timers | grep certbot
```

### 3.4 Update Nginx Config for Production

Replace with full production config:

```bash
sudo tee /etc/nginx/sites-available/masha-osint > /dev/null << 'EOF'
upstream streamlit_backend {
    server 127.0.0.1:8501 fail_timeout=0;
}

# HTTP (redirect to HTTPS)
server {
    listen 80;
    listen [::]:80;
    server_name YOUR_DOMAIN_HERE;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name YOUR_DOMAIN_HERE;

    # SSL certificates (managed by Certbot)
    ssl_certificate /etc/letsencrypt/live/YOUR_DOMAIN_HERE/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/YOUR_DOMAIN_HERE/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/letsencrypt/live/YOUR_DOMAIN_HERE/chain.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Logging
    access_log /var/log/nginx/masha_access.log;
    error_log /var/log/nginx/masha_error.log warn;

    # Timeouts for long AI operations
    proxy_read_timeout 300s;
    proxy_connect_timeout 75s;
    proxy_send_timeout 300s;

    location / {
        proxy_pass http://streamlit_backend;
        proxy_http_version 1.1;

        # WebSocket support (REQUIRED for Streamlit)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Proxy headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;

        # No buffering (real-time updates)
        proxy_buffering off;
        proxy_cache off;
    }

    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }

    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
}
EOF
```

**Replace YOUR_DOMAIN_HERE:**

```bash
sudo sed -i 's/YOUR_DOMAIN_HERE/masha.freirecorporation.com/g' /etc/nginx/sites-available/masha-osint
```

**Reload Nginx:**

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 3.5 Configure Streamlit Settings

```bash
mkdir -p /opt/masha-osint/.streamlit

cat > /opt/masha-osint/.streamlit/config.toml << 'EOF'
[server]
port = 8501
address = "127.0.0.1"
headless = true
enableCORS = false
enableXsrfProtection = true
maxUploadSize = 50

[browser]
gatherUsageStats = false
serverAddress = "YOUR_DOMAIN_HERE"
serverPort = 443

[theme]
base = "dark"
primaryColor = "#00ff00"
backgroundColor = "#0e1117"
secondaryBackgroundColor = "#1c1f26"
textColor = "#fafafa"

[logger]
level = "info"
EOF

# Replace domain
sed -i 's/YOUR_DOMAIN_HERE/masha.freirecorporation.com/g' /opt/masha-osint/.streamlit/config.toml

# Restart service
sudo systemctl restart masha-osint
```

---

## Phase 4: Monitoring & Maintenance

### 4.1 Health Monitoring Script

```bash
sudo tee /usr/local/bin/masha-health-check.sh > /dev/null << 'EOF'
#!/bin/bash
LOG="/var/log/masha-health.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Check service
systemctl is-active --quiet masha-osint
SVC=$?

# Check web endpoint
HTTP=$(curl -s -o /dev/null -w "%{http_code}" https://YOUR_DOMAIN_HERE/health 2>/dev/null || echo "000")

# Log
echo "[$DATE] Service: $SVC | Web: $HTTP" >> $LOG

# Restart if down
if [ $SVC -ne 0 ]; then
    echo "[$DATE] CRITICAL: Restarting service" >> $LOG
    systemctl restart masha-osint
fi
EOF

# Replace domain
sudo sed -i 's/YOUR_DOMAIN_HERE/masha.freirecorporation.com/g' /usr/local/bin/masha-health-check.sh

# Make executable
sudo chmod +x /usr/local/bin/masha-health-check.sh

# Schedule (cron every 5 minutes)
(sudo crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/masha-health-check.sh") | sudo crontab -
```

### 4.2 Daily Backup Script

```bash
sudo tee /usr/local/bin/masha-backup.sh > /dev/null << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/masha/backups"
DATE=$(date '+%Y%m%d_%H%M%S')
BACKUP_FILE="masha-backup-$DATE.tar.gz"

mkdir -p $BACKUP_DIR

tar -czf "$BACKUP_DIR/$BACKUP_FILE" \
    /opt/masha-osint/.env \
    /opt/masha-osint/logs \
    /opt/masha-osint/data \
    /etc/nginx/sites-available/masha-osint \
    /etc/systemd/system/masha-osint.service \
    2>/dev/null

if [ $? -eq 0 ]; then
    echo "[$(date)] Backup created: $BACKUP_FILE ($(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1))" >> /var/log/masha-backup.log

    # Delete backups older than 7 days
    find $BACKUP_DIR -name "masha-backup-*.tar.gz" -mtime +7 -delete
else
    echo "[$(date)] ERROR: Backup failed!" >> /var/log/masha-backup.log
fi
EOF

# Make executable
sudo chmod +x /usr/local/bin/masha-backup.sh

# Schedule daily at 2 AM
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/masha-backup.sh") | crontab -
```

### 4.3 Update Procedure

**Update application:**

```bash
ssh masha@YOUR_VPS_IP
cd /opt/masha-osint

# Pull latest changes
git pull origin main

# If requirements changed
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Restart
sudo systemctl restart masha-osint
sudo systemctl status masha-osint
```

**Update system:**

```bash
sudo apt update && sudo apt upgrade -y

# If kernel updated
sudo reboot
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u masha-osint -n 50 --no-pager

# Common issues:

# 1. Port conflict
sudo lsof -i :8501
# Solution: Kill conflicting process

# 2. Permission error
ls -la /opt/masha-osint/.env
# Should be: -rw------- masha masha

# 3. Missing dependencies
cd /opt/masha-osint
source venv/bin/activate
pip install -r requirements.txt

# 4. Environment variables
cat /opt/masha-osint/.env
# Verify all required keys are set
```

### Nginx Errors

```bash
# Test configuration
sudo nginx -t

# Check logs
sudo tail -f /var/log/nginx/error.log

# Restart
sudo systemctl restart nginx
```

### SSL Certificate Issues

```bash
# Check certificate
sudo certbot certificates

# Renew manually
sudo certbot renew --force-renewal

# Reload Nginx
sudo systemctl reload nginx
```

### Application Errors

```bash
# View real-time logs
sudo journalctl -u masha-osint -f

# Check application logs
ls -lh /opt/masha-osint/logs/
tail -f /opt/masha-osint/logs/*.log

# Verify health
cd /opt/masha-osint
source venv/bin/activate
python health_check.py
```

---

## Verification Checklist

After deployment, verify:

- [ ] Service is running: `sudo systemctl status masha-osint`
- [ ] HTTP redirects to HTTPS: `curl -I http://YOUR_DOMAIN`
- [ ] HTTPS loads correctly: `curl -I https://YOUR_DOMAIN`
- [ ] Web UI is accessible in browser
- [ ] Login works with password from .env
- [ ] Can run test investigation
- [ ] Logs are being created in /opt/masha-osint/logs/
- [ ] SSL certificate auto-renewal: `sudo certbot renew --dry-run`
- [ ] Firewall is active: `sudo ufw status`
- [ ] Fail2Ban is running: `sudo fail2ban-client status`
- [ ] Health check cron is scheduled: `sudo crontab -l`
- [ ] Backup cron is scheduled: `crontab -l`

---

## Useful Commands

### Service Management
```bash
sudo systemctl start masha-osint       # Start
sudo systemctl stop masha-osint        # Stop
sudo systemctl restart masha-osint     # Restart
sudo systemctl status masha-osint      # Status
sudo journalctl -u masha-osint -f      # Live logs
```

### Nginx
```bash
sudo nginx -t                          # Test config
sudo systemctl reload nginx            # Reload
sudo tail -f /var/log/nginx/masha_*.log  # View logs
```

### Application
```bash
cd /opt/masha-osint
source venv/bin/activate
python health_check.py                 # Health check
python main.py -t "target"             # CLI tool
```

### SSL
```bash
sudo certbot certificates              # Check certs
sudo certbot renew                     # Renew
sudo certbot renew --dry-run           # Test renewal
```

---

## Security Best Practices

1. **Never commit .env** - Contains sensitive API keys
2. **Change default password** - Update MASHA_WEB_PASSWORD
3. **Keep system updated** - Regular apt updates
4. **Monitor logs** - Check for suspicious activity
5. **Backup regularly** - Automated daily backups
6. **Use strong passwords** - For all accounts
7. **Enable 2FA on GitHub** - Protect repository
8. **Limit SSH access** - Use SSH keys, disable password auth
9. **Monitor API usage** - SerpAPI and DeepSeek quotas
10. **Test SSL security** - Use SSL Labs scanner

---

## Support

- **GitHub Issues**: https://github.com/freire19/Masha-OSINT/issues
- **Documentation**: https://github.com/freire19/Masha-OSINT
- **Health Check**: `python health_check.py`

---

**End of Deployment Guide**
