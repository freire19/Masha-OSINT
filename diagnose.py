#!/usr/bin/env python3
"""Diagnose deployment issues"""

import paramiko

VPS = {'host': '72.62.166.247', 'user': 'root', 'password': 'EusouISD92@#', 'port': 22}

commands = [
    ("Check if streamlit is installed", "sudo -u masha /opt/masha-osint/venv/bin/streamlit --version"),
    ("Check venv Python", "sudo -u masha /opt/masha-osint/venv/bin/python3 --version"),
    ("List venv packages", "sudo -u masha /opt/masha-osint/venv/bin/pip list | grep -i streamlit"),
    ("Check app.py exists", "ls -la /opt/masha-osint/app.py"),
    ("Check .env exists", "ls -la /opt/masha-osint/.env"),
    ("Check service logs", "journalctl -u masha-osint -n 30 --no-pager"),
    ("Test manual start", "cd /opt/masha-osint && sudo -u masha /opt/masha-osint/venv/bin/streamlit run app.py --server.port=8501 --server.headless=true & sleep 5 && curl http://localhost:8501 && pkill -f streamlit"),
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname=VPS['host'], port=VPS['port'], username=VPS['user'], password=VPS['password'], timeout=30)

for desc, cmd in commands:
    print(f"\n{'='*60}")
    print(f"🔍 {desc}")
    print(f"{'='*60}")
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    output = stdout.read().decode()
    error = stderr.read().decode()
    print(output)
    if error and "warning" not in error.lower():
        print(f"⚠️ Errors: {error}")

ssh.close()
