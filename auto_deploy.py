#!/usr/bin/env python3
"""
Masha OSINT - Autonomous Deployment
Executa deployment completamente automatizado via SSH
"""

import paramiko
import sys
import time

VPS_CONFIG = {
    'host': '72.62.166.247',
    'user': 'root',
    'password': 'EusouISD92@#',
    'port': 22
}

DEPLOYMENT_SCRIPT = """
set -e

echo "🚀 Starting autonomous deployment..."

# Update system
export DEBIAN_FRONTEND=noninteractive
apt update
apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx ufw fail2ban build-essential

# Configure firewall
ufw --force enable
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp

# Create user
if ! id -u masha > /dev/null 2>&1; then
    useradd -m -s /bin/bash masha
    usermod -aG sudo masha
    echo "masha:MashaSecure2024!" | chpasswd
fi

# Setup app directory
mkdir -p /opt/masha-osint
chown masha:masha /opt/masha-osint

# Clone/update repository
cd /opt/masha-osint
if [ -d ".git" ]; then
    sudo -u masha git pull origin main
else
    sudo -u masha git clone https://github.com/freire19/Masha-OSINT.git .
fi

# Install dependencies
sudo -u masha bash << 'VENV_SETUP'
cd /opt/masha-osint
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
VENV_SETUP

# Create .env if not exists
if [ ! -f "/opt/masha-osint/.env" ]; then
    sudo -u masha cp /opt/masha-osint/.env.example /opt/masha-osint/.env
    sudo -u masha chmod 600 /opt/masha-osint/.env
fi

# Create systemd service
cat > /etc/systemd/system/masha-osint.service << 'EOF'
[Unit]
Description=Masha OSINT - Streamlit Web UI
After=network.target

[Service]
Type=simple
User=masha
WorkingDirectory=/opt/masha-osint
Environment="PATH=/opt/masha-osint/venv/bin"
EnvironmentFile=/opt/masha-osint/.env
ExecStart=/opt/masha-osint/venv/bin/streamlit run app.py --server.port=8501 --server.address=127.0.0.1 --server.headless=true --server.enableCORS=false
Restart=always
RestartSec=10
NoNewPrivileges=true
PrivateTmp=true
ReadWritePaths=/opt/masha-osint/logs /opt/masha-osint/data

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable masha-osint

# Configure Nginx
cat > /etc/nginx/sites-available/masha-osint << 'EOF'
upstream streamlit_backend {
    server 127.0.0.1:8501 fail_timeout=0;
}

server {
    listen 80;
    server_name masha.freirecorporation.com;

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

ln -sf /etc/nginx/sites-available/masha-osint /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# Get SSL certificate
certbot --nginx -d masha.freirecorporation.com --non-interactive --agree-tos --email admin@freirecorporation.com --redirect || true

# Configure Streamlit
mkdir -p /opt/masha-osint/.streamlit
cat > /opt/masha-osint/.streamlit/config.toml << 'EOF'
[server]
port = 8501
address = "127.0.0.1"
headless = true
[browser]
serverAddress = "masha.freirecorporation.com"
serverPort = 443
[theme]
base = "dark"
primaryColor = "#00ff00"
EOF
chown -R masha:masha /opt/masha-osint/.streamlit

# Start service
systemctl restart masha-osint

echo "✅ Deployment complete!"
systemctl status masha-osint --no-pager -l | head -15
"""

def deploy():
    """Execute autonomous deployment via SSH"""
    print("🤖 Iniciando deployment autônomo...")
    print(f"📡 Conectando em {VPS_CONFIG['host']}...")

    try:
        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect
        ssh.connect(
            hostname=VPS_CONFIG['host'],
            port=VPS_CONFIG['port'],
            username=VPS_CONFIG['user'],
            password=VPS_CONFIG['password'],
            timeout=30
        )

        print("✅ Conectado!")
        print("🚀 Executando deployment...")

        # Execute deployment
        stdin, stdout, stderr = ssh.exec_command(DEPLOYMENT_SCRIPT, get_pty=True)

        # Stream output in real-time
        while True:
            line = stdout.readline()
            if not line:
                break
            print(line.rstrip())

        # Check exit code
        exit_code = stdout.channel.recv_exit_status()

        if exit_code == 0:
            print("\n✅ Deployment concluído com sucesso!")
            print("🌐 Acesse: https://masha.freirecorporation.com")
            print("\n⚠️  IMPORTANTE: Configure as API keys:")
            print("   ssh root@72.62.166.247")
            print("   nano /opt/masha-osint/.env")
            return True
        else:
            print(f"\n❌ Deployment falhou com código: {exit_code}")
            stderr_output = stderr.read().decode()
            if stderr_output:
                print("Erros:", stderr_output)
            return False

    except paramiko.AuthenticationException:
        print("❌ Erro de autenticação SSH")
        return False
    except paramiko.SSHException as e:
        print(f"❌ Erro SSH: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False
    finally:
        ssh.close()

if __name__ == "__main__":
    success = deploy()
    sys.exit(0 if success else 1)
