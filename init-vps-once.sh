#!/bin/bash
#
# Masha OSINT - VPS Initialization (Run ONCE)
# After this, all deployments are automatic via GitHub Actions
#
# Usage: curl -fsSL https://raw.githubusercontent.com/freire19/Masha-OSINT/main/init-vps-once.sh | bash
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}  🕵️‍♀️  Masha OSINT - Inicialização VPS (Executa UMA VEZ)${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Execute como root: sudo bash ou su -${NC}"
    exit 1
fi

# Get inputs
read -p "Domain (ex: masha.freirecorporation.com): " DOMAIN
read -p "Email para SSL: " EMAIL

# API Keys
echo ""
echo -e "${YELLOW}🔑 Configuração de API Keys:${NC}"
read -p "DeepSeek API Key: " DEEPSEEK_KEY
read -p "SerpAPI Key: " SERPAPI_KEY
read -s -p "Web Password: " WEB_PASSWORD
echo ""

echo ""
echo -e "${YELLOW}[1/9] Atualizando sistema...${NC}"
export DEBIAN_FRONTEND=noninteractive
apt update
apt upgrade -y
apt install -y ufw fail2ban git curl wget vim htop
apt install -y python3 python3-pip python3-venv python3-dev
apt install -y nginx certbot python3-certbot-nginx
apt install -y build-essential libssl-dev libffi-dev libxml2-dev libxslt1-dev

echo -e "${GREEN}✅ Sistema atualizado${NC}"

echo -e "${YELLOW}[2/9] Configurando firewall...${NC}"
ufw --force enable
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp

echo -e "${GREEN}✅ Firewall configurado${NC}"

echo -e "${YELLOW}[3/9] Configurando Fail2Ban...${NC}"
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

echo -e "${GREEN}✅ Fail2Ban configurado${NC}"

echo -e "${YELLOW}[4/9] Criando usuário masha...${NC}"
if ! id -u masha > /dev/null 2>&1; then
    useradd -m -s /bin/bash masha
    usermod -aG sudo masha
    MASHA_PASS=$(openssl rand -base64 16)
    echo "masha:$MASHA_PASS" | chpasswd
    echo -e "${GREEN}✅ Usuário criado (senha: $MASHA_PASS)${NC}"

    if [ -d /root/.ssh ]; then
        mkdir -p /home/masha/.ssh
        cp /root/.ssh/authorized_keys /home/masha/.ssh/ 2>/dev/null || true
        chown -R masha:masha /home/masha/.ssh
        chmod 700 /home/masha/.ssh
        chmod 600 /home/masha/.ssh/authorized_keys 2>/dev/null || true
    fi
else
    echo -e "${YELLOW}Usuário masha já existe${NC}"
fi

echo -e "${YELLOW}[5/9] Clonando aplicação...${NC}"
mkdir -p /opt/masha-osint
chown masha:masha /opt/masha-osint

sudo -u masha bash << 'MASHA_SETUP'
cd /opt/masha-osint
if [ ! -d ".git" ]; then
    git clone https://github.com/freire19/Masha-OSINT.git .
fi

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

mkdir -p logs data
MASHA_SETUP

echo -e "${GREEN}✅ Aplicação clonada${NC}"

echo -e "${YELLOW}[6/9] Configurando environment (.env)...${NC}"
cat > /opt/masha-osint/.env << EOF
# Masha OSINT - Configuração de Produção
DEEPSEEK_API_KEY=$DEEPSEEK_KEY
SERPAPI_KEY=$SERPAPI_KEY
MASHA_WEB_PASSWORD=$WEB_PASSWORD
DEEPSEEK_MODEL=deepseek-reasoner
MASHA_USE_LOCAL_CNPJ_DB=false
EOF

chmod 600 /opt/masha-osint/.env
chown masha:masha /opt/masha-osint/.env

echo -e "${GREEN}✅ Environment configurado${NC}"

echo -e "${YELLOW}[7/9] Criando serviço systemd...${NC}"
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
systemctl start masha-osint

echo -e "${GREEN}✅ Serviço criado e iniciado${NC}"

echo -e "${YELLOW}[8/9] Configurando Nginx...${NC}"
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
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_buffering off;
    }
}
EOF

ln -sf /etc/nginx/sites-available/masha-osint /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl reload nginx

echo -e "${GREEN}✅ Nginx configurado${NC}"

echo -e "${YELLOW}[9/9] Obtendo certificado SSL...${NC}"
certbot --nginx -d ${DOMAIN} \
    --non-interactive \
    --agree-tos \
    --email ${EMAIL} \
    --redirect

if [ -f /etc/letsencrypt/live/${DOMAIN}/fullchain.pem ]; then
    echo -e "${GREEN}✅ SSL configurado${NC}"

    # Update Nginx with full HTTPS config
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

    proxy_read_timeout 300s;

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
    }

    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF

    nginx -t && systemctl reload nginx
else
    echo -e "${RED}⚠️  SSL não configurado. Execute: certbot --nginx -d ${DOMAIN}${NC}"
fi

# Configure Streamlit
mkdir -p /opt/masha-osint/.streamlit
cat > /opt/masha-osint/.streamlit/config.toml << EOF
[server]
port = 8501
address = "127.0.0.1"
headless = true
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false
serverAddress = "${DOMAIN}"
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

chown -R masha:masha /opt/masha-osint/.streamlit

echo ""
echo -e "${BLUE}============================================================${NC}"
echo -e "${GREEN}  ✅ INICIALIZAÇÃO COMPLETA!${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""
echo -e "${GREEN}🎉 Seu VPS está configurado!${NC}"
echo ""
echo -e "${YELLOW}📋 Informações:${NC}"
echo "   Domain: https://${DOMAIN}"
echo "   Status: systemctl status masha-osint"
echo "   Logs: journalctl -u masha-osint -f"
echo ""
echo -e "${YELLOW}🤖 Deployment Automático:${NC}"
echo "   Agora configure os secrets no GitHub:"
echo "   1. Acesse: https://github.com/freire19/Masha-OSINT/settings/secrets/actions"
echo "   2. Adicione os seguintes secrets:"
echo ""
echo "      VPS_HOST: 72.62.166.247"
echo "      VPS_USER: root"
echo "      VPS_PASSWORD: EusouISD92@#"
echo ""
echo -e "${GREEN}   Após configurar, todo 'git push' fará deploy automático!${NC}"
echo ""
echo -e "${BLUE}============================================================${NC}"
