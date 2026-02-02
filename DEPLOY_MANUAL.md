# Manual VPS Deployment - Quick Guide

This guide provides step-by-step commands to deploy Masha OSINT to your VPS.

**VPS Details:**
- IP: 72.62.166.247
- User: root
- Password: EusouISD92@#
- Domain: masha.freirecorporation.com

---

## Step 1: Connect to VPS

```bash
ssh root@72.62.166.247
# Password: EusouISD92@#
```

---

## Step 2: Update System and Install Tools

```bash
apt update && apt upgrade -y
apt install -y ufw fail2ban git curl wget vim htop
apt install -y python3 python3-pip python3-venv python3-dev
apt install -y nginx certbot python3-certbot-nginx
apt install -y build-essential libssl-dev libffi-dev libxml2-dev libxslt1-dev

# Verify Python version
python3 --version
```

---

## Step 3: Configure Firewall

```bash
# Enable and configure UFW
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw --force enable

# Verify
ufw status verbose
```

---

## Step 4: Configure Fail2Ban

```bash
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
```

---

## Step 5: Create Non-Root User

```bash
# Create masha user
useradd -m -s /bin/bash masha
usermod -aG sudo masha

# Set password (choose a strong one)
passwd masha

# Optional: Copy SSH keys
mkdir -p /home/masha/.ssh
cp /root/.ssh/authorized_keys /home/masha/.ssh/ 2>/dev/null || true
chown -R masha:masha /home/masha/.ssh
chmod 700 /home/masha/.ssh
chmod 600 /home/masha/.ssh/authorized_keys 2>/dev/null || true
```

---

## Step 6: Setup Application

```bash
# Switch to masha user
su - masha

# Create directory
sudo mkdir -p /opt/masha-osint
sudo chown masha:masha /opt/masha-osint
cd /opt/masha-osint

# Clone repository
git clone https://github.com/freire19/Masha-OSINT.git .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # ADD YOUR API KEYS HERE!
```

**IMPORTANT: Edit .env file and add your real API keys:**

```bash
DEEPSEEK_API_KEY=sk-your-actual-deepseek-key
SERPAPI_KEY=your-actual-serpapi-key
MASHA_WEB_PASSWORD=your-secure-password
```

```bash
# Secure .env
chmod 600 .env

# Test installation
python health_check.py

# Exit from masha user back to root
exit
```

---

## Step 7: Create Systemd Service

```bash
# As root, create service file
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

# Enable and start service
systemctl daemon-reload
systemctl enable masha-osint
systemctl start masha-osint

# Check status
systemctl status masha-osint

# Test locally
curl http://localhost:8501
```

---

## Step 8: Configure Nginx (HTTP First)

```bash
# Create temporary HTTP-only config
cat > /etc/nginx/sites-available/masha-osint << 'EOF'
upstream streamlit_backend {
    server 127.0.0.1:8501 fail_timeout=0;
}

server {
    listen 80;
    listen [::]:80;
    server_name masha.freirecorporation.com;

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

# Enable site
ln -s /etc/nginx/sites-available/masha-osint /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default

# Test and reload
nginx -t
systemctl reload nginx
```

---

## Step 9: Obtain SSL Certificate

```bash
# Verify DNS is pointing to VPS
dig +short masha.freirecorporation.com
# Should return: 72.62.166.247

# Obtain certificate
certbot --nginx -d masha.freirecorporation.com

# Follow prompts:
# Email: your-email@example.com
# Agree to ToS: Y
# Share email: N (optional)
```

---

## Step 10: Update Nginx Config (HTTPS)

```bash
# Replace with full HTTPS config
cat > /etc/nginx/sites-available/masha-osint << 'EOF'
upstream streamlit_backend {
    server 127.0.0.1:8501 fail_timeout=0;
}

# HTTP (redirect to HTTPS)
server {
    listen 80;
    listen [::]:80;
    server_name masha.freirecorporation.com;

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
    server_name masha.freirecorporation.com;

    ssl_certificate /etc/letsencrypt/live/masha.freirecorporation.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/masha.freirecorporation.com/privkey.pem;

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

        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

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

# Test and reload
nginx -t
systemctl reload nginx
```

---

## Step 11: Configure Streamlit

```bash
# Create Streamlit config
mkdir -p /opt/masha-osint/.streamlit

cat > /opt/masha-osint/.streamlit/config.toml << 'EOF'
[server]
port = 8501
address = "127.0.0.1"
headless = true
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false
serverAddress = "masha.freirecorporation.com"
serverPort = 443

[theme]
base = "dark"
primaryColor = "#00ff00"

[logger]
level = "info"
EOF

# Set ownership
chown -R masha:masha /opt/masha-osint/.streamlit

# Restart service
systemctl restart masha-osint
```

---

## Step 12: Verification

```bash
# Check service status
systemctl status masha-osint

# Check logs
journalctl -u masha-osint -n 50

# Test HTTP redirect
curl -I http://masha.freirecorporation.com

# Test HTTPS
curl -I https://masha.freirecorporation.com

# Test health endpoint
curl https://masha.freirecorporation.com/health
```

**Open in browser:**
```
https://masha.freirecorporation.com
```

---

## Step 13: Setup Monitoring (Optional)

### Health Check Script

```bash
cat > /usr/local/bin/masha-health-check.sh << 'EOF'
#!/bin/bash
LOG="/var/log/masha-health.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

systemctl is-active --quiet masha-osint
SVC=$?

HTTP=$(curl -s -o /dev/null -w "%{http_code}" https://masha.freirecorporation.com/health 2>/dev/null || echo "000")

echo "[$DATE] Service: $SVC | Web: $HTTP" >> $LOG

if [ $SVC -ne 0 ]; then
    echo "[$DATE] CRITICAL: Restarting service" >> $LOG
    systemctl restart masha-osint
fi
EOF

chmod +x /usr/local/bin/masha-health-check.sh

# Schedule every 5 minutes
crontab -l 2>/dev/null | { cat; echo "*/5 * * * * /usr/local/bin/masha-health-check.sh"; } | crontab -
```

### Backup Script

```bash
cat > /usr/local/bin/masha-backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/masha/backups"
DATE=$(date '+%Y%m%d_%H%M%S')
BACKUP_FILE="masha-backup-$DATE.tar.gz"

mkdir -p $BACKUP_DIR

tar -czf "$BACKUP_DIR/$BACKUP_FILE" \
    /opt/masha-osint/.env \
    /opt/masha-osint/logs \
    /opt/masha-osint/data \
    2>/dev/null

find $BACKUP_DIR -name "masha-backup-*.tar.gz" -mtime +7 -delete
EOF

chmod +x /usr/local/bin/masha-backup.sh

# Schedule daily at 2 AM
su - masha -c 'crontab -l 2>/dev/null | { cat; echo "0 2 * * * /usr/local/bin/masha-backup.sh"; } | crontab -'
```

---

## Verification Checklist

- [ ] Service running: `systemctl status masha-osint`
- [ ] HTTP redirects to HTTPS
- [ ] HTTPS loads web UI
- [ ] Can login with password
- [ ] Can run test investigation
- [ ] Logs are created: `ls -lh /opt/masha-osint/logs/`
- [ ] SSL auto-renewal: `certbot renew --dry-run`
- [ ] Firewall active: `ufw status`
- [ ] Fail2Ban active: `systemctl status fail2ban`

---

## Useful Commands

```bash
# Service management
systemctl start masha-osint
systemctl stop masha-osint
systemctl restart masha-osint
systemctl status masha-osint

# View logs
journalctl -u masha-osint -f                    # Live logs
journalctl -u masha-osint -n 100                # Last 100 lines
tail -f /var/log/nginx/masha_access.log         # Nginx access logs
tail -f /var/log/nginx/masha_error.log          # Nginx error logs

# Update application
su - masha
cd /opt/masha-osint
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
exit
systemctl restart masha-osint

# SSL management
certbot certificates                             # Check certs
certbot renew                                    # Renew certs
certbot renew --dry-run                          # Test renewal
```

---

## Troubleshooting

### Service won't start
```bash
# Check logs
journalctl -u masha-osint -n 50

# Check if port is in use
lsof -i :8501

# Check permissions
ls -la /opt/masha-osint/.env
```

### Can't access website
```bash
# Check Nginx
nginx -t
systemctl status nginx

# Check firewall
ufw status

# Check DNS
dig +short masha.freirecorporation.com
```

### SSL issues
```bash
# Check certificate
certbot certificates

# Renew manually
certbot renew --force-renewal

# Check Nginx config
nginx -t
```

---

**Deployment Complete! 🎉**

Access your OSINT platform at:
**https://masha.freirecorporation.com**
