#!/usr/bin/env python3
"""Verify deployment is working"""

import paramiko
import time

VPS = {'host': '72.62.166.247', 'user': 'root', 'password': 'EusouISD92@#', 'port': 22}

commands = [
    ("Service status", "systemctl is-active masha-osint"),
    ("Test local connection", "curl -s http://localhost:8501 | head -20"),
    ("Test HTTPS", "curl -Isk https://masha.freirecorporation.com | head -20"),
    ("Service logs", "journalctl -u masha-osint -n 20 --no-pager"),
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname=VPS['host'], port=VPS['port'], username=VPS['user'], password=VPS['password'], timeout=30)

print("🔍 Verificando deployment...\n")

for desc, cmd in commands:
    print(f"{'='*60}")
    print(f"📋 {desc}")
    print(f"{'='*60}")
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    time.sleep(2)  # Wait for output
    output = stdout.read().decode()
    print(output)
    print()

ssh.close()

print("\n" + "="*60)
print("✅ Verificação completa!")
print("="*60)
print("\n🌐 Acesse: https://masha.freirecorporation.com")
print("\n⚠️  Configure as API keys antes de usar:")
print("   ssh root@72.62.166.247")
print("   nano /opt/masha-osint/.env")
