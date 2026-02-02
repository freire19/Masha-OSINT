#!/usr/bin/env python3
"""
Migrate Masha OSINT to CloudPanel
"""

import paramiko
import time

VPS = {'host': '72.62.166.247', 'user': 'root', 'password': 'EusouISD92@#', 'port': 22}

migration_script = """
set -e

echo "🔍 [1/8] Investigando estrutura do CloudPanel..."

# Check CloudPanel CLI
if command -v clpctl &> /dev/null; then
    echo "✅ CloudPanel CLI encontrado"
    clpctl --version
else
    echo "⚠️  CloudPanel CLI não encontrado, usando comandos manuais"
fi

# Find CloudPanel structure
if [ -d "/home/cloudpanel" ]; then
    echo "✅ CloudPanel instalado em /home/cloudpanel"
    ls -la /home/cloudpanel/ | head -10
else
    echo "⚠️  Estrutura CloudPanel não encontrada"
fi

echo ""
echo "🌐 [2/8] Parando serviço antigo e criando site..."

# Stop old service
systemctl stop masha-osint || true

# Create user if doesn't exist
if ! id -u masha-osint > /dev/null 2>&1; then
    useradd -m -s /bin/bash masha-osint
    SITE_PASSWORD=$(openssl rand -base64 16)
    echo "masha-osint:$SITE_PASSWORD" | chpasswd
    echo "✅ Usuário masha-osint criado (senha: $SITE_PASSWORD)"
fi

# Create site directory structure
mkdir -p /home/masha-osint/htdocs/masha.freirecorporation.com
mkdir -p /home/masha-osint/logs
chown -R masha-osint:masha-osint /home/masha-osint

# Try CloudPanel CLI if available
if command -v clpctl &> /dev/null; then
    SITE_PASSWORD=$(openssl rand -base64 16)
    clpctl site:add:python --domainName=masha.freirecorporation.com --pythonVersion=3.12 --appPort=8501 --siteUser=masha-osint --siteUserPassword="$SITE_PASSWORD" 2>&1 || {
        echo "⚠️  CloudPanel CLI failed, continuing with manual setup..."
    }
fi

echo ""
echo "📦 [3/8] Configurando aplicação no CloudPanel..."

# Site directory
SITE_DIR="/home/masha-osint/htdocs/masha.freirecorporation.com"

# Clean and recreate if exists with files
if [ -d "$SITE_DIR" ] && [ "$(ls -A $SITE_DIR)" ]; then
    echo "Directory exists with files, cleaning..."
    rm -rf $SITE_DIR
fi

mkdir -p $SITE_DIR
chown -R masha-osint:masha-osint $SITE_DIR

# Clone repository
cd /home/masha-osint/htdocs
echo "Cloning repository..."
sudo -u masha-osint git clone https://github.com/freire19/Masha-OSINT.git masha.freirecorporation.com

# Copy .env from old location if exists
if [ -f "/opt/masha-osint/.env" ]; then
    echo "Copying .env from old location..."
    cp /opt/masha-osint/.env $SITE_DIR/.env
    chown masha-osint:masha-osint $SITE_DIR/.env
    chmod 600 $SITE_DIR/.env
fi

echo ""
echo "🐍 [4/8] Configurando Python venv..."

# Create venv
cd $SITE_DIR
sudo -u masha-osint python3 -m venv venv --clear
sudo -u masha-osint $SITE_DIR/venv/bin/pip install --upgrade pip
sudo -u masha-osint $SITE_DIR/venv/bin/pip install streamlit==1.40.0
sudo -u masha-osint $SITE_DIR/venv/bin/pip install -r $SITE_DIR/requirements.txt

# Create .env if not exists
if [ ! -f "$SITE_DIR/.env" ]; then
    sudo -u masha-osint cat > $SITE_DIR/.env << 'EOF'
# Masha OSINT - Environment Configuration
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SERPAPI_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
RAPIDAPI_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DEEPSEEK_MODEL=deepseek-reasoner
MASHA_WEB_PASSWORD=CHANGE_THIS_PASSWORD
MASHA_USE_LOCAL_CNPJ_DB=false
EOF
    chmod 600 $SITE_DIR/.env
fi

echo ""
echo "⚙️  [5/8] Criando serviço systemd..."

# Update systemd service to use CloudPanel directory
cat > /etc/systemd/system/masha-osint.service << EOF
[Unit]
Description=Masha OSINT - Streamlit (CloudPanel)
After=network.target

[Service]
Type=simple
User=masha-osint
Group=masha-osint
WorkingDirectory=$SITE_DIR
Environment="PATH=$SITE_DIR/venv/bin"
EnvironmentFile=$SITE_DIR/.env
ExecStart=$SITE_DIR/venv/bin/streamlit run app.py --server.port=8501 --server.address=127.0.0.1 --server.headless=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable masha-osint
systemctl restart masha-osint

echo ""
echo "🌐 [6/8] Configurando Nginx vhost..."

# Create CloudPanel-compatible vhost
cat > /etc/nginx/sites-available/masha.freirecorporation.com.conf << 'EOF'
upstream streamlit_masha {
    server 127.0.0.1:8501 fail_timeout=0;
}

server {
    listen 80;
    listen [::]:80;
    server_name masha.freirecorporation.com;

    # CloudPanel integration
    access_log /home/masha-osint/logs/access.log;
    error_log /home/masha-osint/logs/error.log;

    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        proxy_pass http://streamlit_masha;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_buffering off;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/masha.freirecorporation.com.conf /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/masha-osint

nginx -t && systemctl reload nginx

echo ""
echo "🔒 [7/8] Configurando SSL..."

# Get SSL certificate
certbot --nginx -d masha.freirecorporation.com --non-interactive --agree-tos --email admin@freirecorporation.com --redirect || {
    echo "Trying certonly..."
    certbot certonly --webroot -w /var/www/html -d masha.freirecorporation.com --non-interactive --agree-tos --email admin@freirecorporation.com
}

# Update vhost with HTTPS if certificate exists
if [ -f /etc/letsencrypt/live/masha.freirecorporation.com/fullchain.pem ]; then
cat > /etc/nginx/sites-available/masha.freirecorporation.com.conf << 'EOF'
upstream streamlit_masha {
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
        return 301 https://\$server_name\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name masha.freirecorporation.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/masha.freirecorporation.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/masha.freirecorporation.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # CloudPanel integration
    access_log /home/masha-osint/logs/access.log;
    error_log /home/masha-osint/logs/error.log;

    location / {
        proxy_pass http://streamlit_masha;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_buffering off;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    location /health {
        access_log off;
        return 200 "healthy\\n";
        add_header Content-Type text/plain;
    }
}
EOF
    nginx -t && systemctl reload nginx
fi

echo ""
echo "🎨 [8/8] Configurando Streamlit..."

mkdir -p $SITE_DIR/.streamlit
cat > $SITE_DIR/.streamlit/config.toml << 'EOF'
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
backgroundColor = "#0e1117"
secondaryBackgroundColor = "#1c1f26"
textColor = "#fafafa"

[logger]
level = "info"
EOF

chown -R masha-osint:masha-osint $SITE_DIR/.streamlit

echo ""
echo "============================================================"
echo "✅ MIGRAÇÃO PARA CLOUDPANEL COMPLETA!"
echo "============================================================"
echo ""
echo "📋 Informações:"
echo "   Site: https://masha.freirecorporation.com"
echo "   Diretório: $SITE_DIR"
echo "   Usuário: masha-osint"
echo "   Logs: /home/masha-osint/logs/"
echo ""
echo "🔧 Comandos úteis:"
echo "   Status: systemctl status masha-osint"
echo "   Logs: journalctl -u masha-osint -f"
echo "   Reiniciar: systemctl restart masha-osint"
echo ""
echo "⚠️  IMPORTANTE: Configure as API keys em:"
echo "   $SITE_DIR/.env"
echo ""
"""

def migrate():
    """Execute migration to CloudPanel"""
    print("============================================================")
    print(" 🔄 Migrando Masha OSINT para CloudPanel")
    print("============================================================")
    print(f"VPS: {VPS['host']}")
    print(f"Domain: masha.freirecorporation.com")
    print("")

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        print("📡 Conectando no VPS...")
        ssh.connect(
            hostname=VPS['host'],
            port=VPS['port'],
            username=VPS['user'],
            password=VPS['password'],
            timeout=30
        )

        print("✅ Conectado!")
        print("🚀 Executando migração...\n")

        # Execute migration
        stdin, stdout, stderr = ssh.exec_command(migration_script, get_pty=True)

        # Stream output in real-time
        while True:
            line = stdout.readline()
            if not line:
                break
            print(line.rstrip())

        # Check exit code
        exit_code = stdout.channel.recv_exit_status()

        if exit_code == 0:
            print("\n" + "="*60)
            print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("="*60)
            print("\n🌐 Site: https://masha.freirecorporation.com")
            print("📁 Diretório: /home/masha-osint/htdocs/masha.freirecorporation.com")
            print("\n⚠️  Configure as API keys:")
            print("   ssh root@72.62.166.247")
            print("   nano /home/masha-osint/htdocs/masha.freirecorporation.com/.env")
            print("   systemctl restart masha-osint")
            return True
        else:
            print(f"\n❌ Migração falhou com código: {exit_code}")
            return False

    except Exception as e:
        print(f"\n❌ Erro: {e}")
        return False
    finally:
        ssh.close()

if __name__ == "__main__":
    import sys
    success = migrate()
    sys.exit(0 if success else 1)
