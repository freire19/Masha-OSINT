# 🎉 Masha OSINT - CloudPanel Deployment

## ✅ Status Atual

**URL:** https://masha.freirecorporation.com
**Status:** ✅ ONLINE E FUNCIONANDO
**Infraestrutura:** CloudPanel 6.0.8
**Usuário:** masha-osint
**Diretório:** `/home/masha-osint/htdocs/masha.freirecorporation.com`

---

## 🚀 Deployment Automático (Recomendado)

### Execute UMA linha:

```bash
python3 auto_deploy_cloudpanel.py
```

**Isso vai:**
1. ✅ Conectar no VPS via SSH
2. ✅ Puxar código atualizado do GitHub
3. ✅ Instalar/atualizar dependências
4. ✅ Reiniciar o serviço
5. ✅ Verificar que está funcionando

**Tempo:** ~30 segundos
**Intervenção:** ZERO

---

## 📁 Estrutura no CloudPanel

```
/home/masha-osint/
├── htdocs/
│   └── masha.freirecorporation.com/    # Aplicação principal
│       ├── app.py                      # Streamlit web UI
│       ├── main.py                     # CLI tool
│       ├── .env                        # API Keys (privado)
│       ├── venv/                       # Python virtual environment
│       ├── src/                        # Código fonte
│       │   ├── agents/                 # Agentes de investigação
│       │   ├── tools/                  # Ferramentas OSINT
│       │   └── utils/                  # Utilidades
│       ├── logs/                       # Logs da aplicação
│       └── .streamlit/                 # Config Streamlit
└── logs/                               # Logs do Nginx
    ├── access.log
    └── error.log
```

---

## ⚙️ Configuração Inicial

### Configure as API Keys (OBRIGATÓRIO)

```bash
ssh root@72.62.166.247
nano /home/masha-osint/htdocs/masha.freirecorporation.com/.env
```

Edite e adicione suas chaves reais:

```bash
DEEPSEEK_API_KEY=sk-your-actual-key
SERPAPI_KEY=your-actual-key
RAPIDAPI_KEY=your-actual-key (opcional)
MASHA_WEB_PASSWORD=your-secure-password
```

Depois reinicie:

```bash
systemctl restart masha-osint
```

---

## 🔧 Comandos Úteis

### Status do Serviço
```bash
ssh root@72.62.166.247 "systemctl status masha-osint"
```

### Ver Logs em Tempo Real
```bash
ssh root@72.62.166.247 "journalctl -u masha-osint -f"
```

### Reiniciar Serviço
```bash
ssh root@72.62.166.247 "systemctl restart masha-osint"
```

### Logs do Nginx
```bash
ssh root@72.62.166.247 "tail -f /home/masha-osint/logs/access.log"
ssh root@72.62.166.247 "tail -f /home/masha-osint/logs/error.log"
```

### Atualizar Manualmente
```bash
ssh root@72.62.166.247
cd /home/masha-osint/htdocs/masha.freirecorporation.com
sudo -u masha-osint git pull origin main
sudo -u masha-osint ./venv/bin/pip install -r requirements.txt
systemctl restart masha-osint
```

---

## 🏗️ Infraestrutura

### Serviço Systemd
- **Nome:** `masha-osint.service`
- **Usuário:** `masha-osint`
- **Descrição:** Masha OSINT - Streamlit (CloudPanel)
- **Port:** 8501 (interno)
- **Auto-restart:** Sim

### Nginx Reverse Proxy
- **Config:** `/etc/nginx/sites-available/masha.freirecorporation.com.conf`
- **Porta Externa:** 443 (HTTPS)
- **SSL:** Let's Encrypt (renovação automática)
- **Redirect HTTP→HTTPS:** Sim

### CloudPanel Integration
- **CLI:** `clpctl` (CloudPanel 6.0.8)
- **User:** `masha-osint` (gerenciado pelo CloudPanel)
- **Logs:** Integrados com CloudPanel

---

## 🔄 Workflow de Desenvolvimento

```bash
# 1. Fazer mudanças localmente
vim app.py

# 2. Testar localmente
streamlit run app.py

# 3. Commit
git add .
git commit -m "Update feature X"

# 4. Push
git push origin main

# 5. Deploy (quando quiser)
python3 auto_deploy_cloudpanel.py

# Pronto! Em produção em ~30 segundos 🚀
```

---

## 📊 Monitoramento

### Verificar Status Completo
```bash
python3 verify_deploy.py
```

### CloudPanel Dashboard
Acesse o painel do CloudPanel para:
- Monitorar recursos (CPU, RAM, Disk)
- Ver estatísticas de tráfego
- Gerenciar SSL
- Visualizar logs

### Uptime Monitoring (Recomendado)
Configure monitoramento externo:
- https://uptimerobot.com
- https://www.pingdom.com
- https://www.statuspage.io

---

## 🔒 Segurança

### Implementado
- ✅ Firewall UFW ativo
- ✅ Fail2Ban configurado
- ✅ SSL/TLS com Let's Encrypt
- ✅ HTTPS obrigatório (redirect automático)
- ✅ Usuário não-root (masha-osint)
- ✅ .env com permissões restritas (600)
- ✅ Security headers (HSTS, X-Frame-Options, etc)

### Recomendações Adicionais
```bash
# 1. Configure backup automático
ssh root@72.62.166.247
crontab -e
# Adicione:
# 0 2 * * * tar -czf /root/backups/masha-$(date +\%Y\%m\%d).tar.gz /home/masha-osint

# 2. Limite rate do Nginx (se necessário)
# Em /etc/nginx/sites-available/masha.freirecorporation.com.conf
# Adicione: limit_req_zone $binary_remote_addr zone=masha:10m rate=10r/s;

# 3. Configure monitoramento de logs
# Instale logwatch ou similar
apt install logwatch
```

---

## 🚨 Troubleshooting

### Serviço não inicia
```bash
# Ver logs de erro
journalctl -u masha-osint -n 50

# Verificar API keys
cat /home/masha-osint/htdocs/masha.freirecorporation.com/.env

# Testar manualmente
cd /home/masha-osint/htdocs/masha.freirecorporation.com
source venv/bin/activate
streamlit run app.py
```

### Site não carrega
```bash
# Verificar Nginx
nginx -t
systemctl status nginx

# Ver logs do Nginx
tail -f /home/masha-osint/logs/error.log

# Testar localmente
curl -I http://localhost:8501
curl -Ik https://masha.freirecorporation.com
```

### Dependências com problemas
```bash
# Reinstalar venv
cd /home/masha-osint/htdocs/masha.freirecorporation.com
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
systemctl restart masha-osint
```

### Re-deployment completo
```bash
# Se algo der muito errado, execute:
python3 migrate_to_cloudpanel.py
```

---

## 🎯 Comparação: Antes vs Depois

### Antes (Deployment Manual)
```
├── /opt/masha-osint/          # Fora do CloudPanel
├── Configuração manual
├── SSL manual
├── Monitoramento separado
└── Sem integração CloudPanel
```

### Depois (CloudPanel Integration)
```
├── /home/masha-osint/htdocs/  # Integrado ao CloudPanel
├── Usuário CloudPanel
├── SSL gerenciado
├── Logs centralizados
├── Interface web de gerenciamento
└── Deployment automático: python3 auto_deploy_cloudpanel.py
```

---

## ✨ Benefícios do CloudPanel

1. **Gerenciamento Web** - Interface visual para gerenciar o site
2. **SSL Automático** - Renovação automática de certificados
3. **Logs Centralizados** - Todos os logs em um lugar
4. **Backups Fáceis** - Integração com sistema de backup
5. **Monitoramento** - Métricas de CPU, RAM, disco
6. **Multi-site** - Fácil adicionar mais sites no mesmo VPS

---

## 📝 Scripts Disponíveis

| Script | Descrição | Uso |
|--------|-----------|-----|
| `auto_deploy_cloudpanel.py` | Deployment automático | Deploy regular |
| `migrate_to_cloudpanel.py` | Migração para CloudPanel | Executado uma vez |
| `verify_deploy.py` | Verificar deployment | Diagnóstico |
| `diagnose.py` | Diagnóstico completo | Troubleshooting |
| `auto_deploy.py` | Deploy antigo (legado) | Não usar mais |

---

## 🎉 Resultado Final

✅ **Sistema 100% Autônomo e Integrado!**

- **Deployment:** `python3 auto_deploy_cloudpanel.py` (~30 segundos)
- **Gerenciamento:** Via CloudPanel web interface
- **Monitoramento:** Logs centralizados e métricas
- **Segurança:** SSL, Firewall, Fail2Ban
- **Escalabilidade:** Fácil adicionar mais recursos

**Sua plataforma OSINT está em produção!** 🚀
🌐 https://masha.freirecorporation.com

---

## 📞 Suporte

### Documentação
- [DEPLOYMENT_SUCCESS.md](DEPLOYMENT_SUCCESS.md) - Guia inicial
- [CI-CD.md](CI-CD.md) - Automação e CI/CD
- Este arquivo - CloudPanel específico

### CloudPanel
- Docs: https://www.cloudpanel.io/docs/
- CLI: `clpctl --help`
- Community: https://community.cloudpanel.io/

### Masha OSINT
- GitHub: https://github.com/freire19/Masha-OSINT
- Issues: https://github.com/freire19/Masha-OSINT/issues
