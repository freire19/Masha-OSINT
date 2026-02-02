#!/usr/bin/env python3
"""
Masha OSINT - Autonomous Deployment to CloudPanel
Run this script to deploy automatically to your VPS
"""

import paramiko
import sys

VPS_CONFIG = {
    'host': '72.62.166.247',
    'user': 'root',
    'password': 'EusouISD92@#',
    'port': 22
}

SITE_DIR = "/home/masha-osint/htdocs/masha.freirecorporation.com"

DEPLOYMENT_SCRIPT = f"""
set -e

echo "🚀 Starting CloudPanel deployment..."

# Navigate to site directory
cd {SITE_DIR}

# Pull latest code
echo "📥 Pulling latest code..."
sudo -u masha-osint git pull origin main

# Update dependencies
echo "📦 Updating dependencies..."
sudo -u masha-osint {SITE_DIR}/venv/bin/pip install --upgrade pip -q
sudo -u masha-osint {SITE_DIR}/venv/bin/pip install streamlit==1.40.0 -q
sudo -u masha-osint {SITE_DIR}/venv/bin/pip install -r {SITE_DIR}/requirements.txt -q

# Ensure proper permissions
chown -R masha-osint:masha-osint {SITE_DIR}
chmod 600 {SITE_DIR}/.env

# Restart service
echo "🔄 Restarting service..."
systemctl restart masha-osint

# Wait for service to start
sleep 3

# Verify service
if systemctl is-active --quiet masha-osint; then
    echo ""
    echo "✅ DEPLOYMENT SUCCESSFUL!"
    echo ""
    echo "Service status:"
    systemctl status masha-osint --no-pager -l | head -10
    echo ""
    echo "🌐 Site: https://masha.freirecorporation.com"
else
    echo ""
    echo "❌ Service failed to start"
    echo ""
    echo "Logs:"
    journalctl -u masha-osint -n 20 --no-pager
    exit 1
fi
"""

def deploy():
    """Execute autonomous deployment"""
    print("=" * 60)
    print(" 🤖 Autonomous Deployment - Masha OSINT (CloudPanel)")
    print("=" * 60)
    print(f"VPS: {VPS_CONFIG['host']}")
    print(f"Site: https://masha.freirecorporation.com")
    print("")

    try:
        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect
        print("📡 Connecting to VPS...")
        ssh.connect(
            hostname=VPS_CONFIG['host'],
            port=VPS_CONFIG['port'],
            username=VPS_CONFIG['user'],
            password=VPS_CONFIG['password'],
            timeout=30
        )

        print("✅ Connected!")
        print("🚀 Executing deployment...\n")

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
            print("\n" + "="*60)
            print("✅ DEPLOYMENT COMPLETED SUCCESSFULLY!")
            print("="*60)
            print("\n🎉 Your changes are now live!")
            print("🌐 Access: https://masha.freirecorporation.com")
            return True
        else:
            print(f"\n❌ Deployment failed with code: {exit_code}")
            return False

    except paramiko.AuthenticationException:
        print("❌ SSH authentication failed")
        return False
    except paramiko.SSHException as e:
        print(f"❌ SSH error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        ssh.close()

if __name__ == "__main__":
    success = deploy()
    sys.exit(0 if success else 1)
