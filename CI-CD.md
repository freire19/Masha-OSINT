# 🤖 CI/CD Automático - Masha OSINT

## Deploy Automático com GitHub Actions

Toda vez que você fizer `git push`, o deployment acontece **automaticamente** no VPS.

---

## 🚀 Setup Inicial (Uma Vez)

### Passo 1: Inicializar VPS

Execute **UMA VEZ** no VPS:

```bash
ssh root@72.62.166.247
curl -fsSL https://raw.githubusercontent.com/freire19/Masha-OSINT/main/init-vps-once.sh | bash
```

O script vai pedir:
- Domain: `masha.freirecorporation.com`
- Email: Seu email para SSL
- DeepSeek API Key
- SerpAPI Key
- Web Password

### Passo 2: Configurar GitHub Secrets

1. Acesse: https://github.com/freire19/Masha-OSINT/settings/secrets/actions

2. Clique em **"New repository secret"**

3. Adicione os seguintes secrets:

| Name | Value |
|------|-------|
| `VPS_HOST` | `72.62.166.247` |
| `VPS_USER` | `root` |
| `VPS_PASSWORD` | `EusouISD92@#` |

### Passo 3: Pronto!

Agora, toda vez que você der `git push`, o GitHub Actions:
- ✅ Detecta o push automaticamente
- ✅ Conecta no VPS via SSH
- ✅ Puxa o código mais recente
- ✅ Instala/atualiza dependências
- ✅ Reinicia o serviço
- ✅ Verifica que está funcionando

---

## 📋 Como Usar

### Deploy Automático (Normal)

```bash
# Faça suas mudanças
git add .
git commit -m "Update feature X"
git push origin main

# GitHub Actions faz o deploy automaticamente! 🎉
```

### Deploy Manual (Se Necessário)

1. Acesse: https://github.com/freire19/Masha-OSINT/actions
2. Clique em **"Deploy to VPS"**
3. Clique em **"Run workflow"**
4. Selecione branch `main`
5. Clique em **"Run workflow"**

---

## 🔍 Monitorar Deployment

### Ver Logs do GitHub Actions

1. Acesse: https://github.com/freire19/Masha-OSINT/actions
2. Clique no último workflow
3. Veja os logs em tempo real

### Ver Status no VPS

```bash
ssh root@72.62.166.247

# Status do serviço
systemctl status masha-osint

# Logs em tempo real
journalctl -u masha-osint -f

# Últimas 50 linhas
journalctl -u masha-osint -n 50
```

---

## 🛠️ Como Funciona

### Workflow do GitHub Actions

```
┌─────────────┐
│  git push   │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  GitHub detecta     │
│  push na main       │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  GitHub Actions     │
│  inicia workflow    │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  Conecta no VPS     │
│  via SSH            │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  git pull           │
│  pip install        │
│  systemctl restart  │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  Verifica se está   │
│  funcionando        │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  ✅ Deploy completo │
└─────────────────────┘
```

### Arquivo de Workflow

Localização: `.github/workflows/deploy.yml`

**O que ele faz:**

1. **Checkout**: Baixa o código do repositório
2. **Deploy**: Conecta no VPS e executa:
   - Pull do código mais recente
   - Atualiza dependências Python
   - Reinicia o serviço systemd
3. **Verify**: Verifica se o serviço está rodando

---

## 📝 Estrutura de Deployment

### No VPS:

```
/opt/masha-osint/
├── app.py                      # Aplicação principal
├── main.py                     # CLI tool
├── requirements.txt            # Dependências
├── .env                        # API Keys (não no git)
├── venv/                       # Virtual environment
├── src/                        # Código fonte
├── logs/                       # Logs da aplicação
└── .streamlit/config.toml      # Config do Streamlit

/etc/systemd/system/
└── masha-osint.service         # Serviço systemd

/etc/nginx/sites-available/
└── masha-osint                 # Config do Nginx
```

---

## 🔧 Troubleshooting

### Deployment Falhou no GitHub Actions

1. Ver logs: https://github.com/freire19/Masha-OSINT/actions
2. Verificar secrets estão configurados corretamente
3. Testar conexão SSH manualmente:
   ```bash
   ssh root@72.62.166.247
   ```

### Serviço Não Inicia

```bash
# Ver logs de erro
journalctl -u masha-osint -n 100

# Verificar .env
cat /opt/masha-osint/.env

# Testar manualmente
cd /opt/masha-osint
source venv/bin/activate
streamlit run app.py
```

### Nginx Erro

```bash
# Testar config
nginx -t

# Ver logs
tail -f /var/log/nginx/error.log

# Reiniciar
systemctl restart nginx
```

---

## 🚨 Comandos de Emergência

### Rollback para Versão Anterior

```bash
ssh root@72.62.166.247

cd /opt/masha-osint
git log --oneline -10               # Ver últimos commits
git checkout <commit-hash>          # Voltar para commit específico
systemctl restart masha-osint       # Reiniciar
```

### Atualização Manual

```bash
ssh root@72.62.166.247

cd /opt/masha-osint
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
systemctl restart masha-osint
```

### Ver Status Completo

```bash
ssh root@72.62.166.247

# Serviço
systemctl status masha-osint

# Nginx
systemctl status nginx

# Certificado SSL
certbot certificates

# Firewall
ufw status

# Processos
ps aux | grep streamlit

# Portas
netstat -tulpn | grep 8501
```

---

## 📊 Métricas e Logs

### Logs da Aplicação

```bash
# Logs do serviço
journalctl -u masha-osint -f

# Logs das investigações
ls -lh /opt/masha-osint/logs/
tail -f /opt/masha-osint/logs/*.json
```

### Logs do Nginx

```bash
# Access log
tail -f /var/log/nginx/masha_access.log

# Error log
tail -f /var/log/nginx/masha_error.log
```

### Monitoramento em Tempo Real

```bash
# CPU e memória
htop

# Uso de disco
df -h

# Status geral
systemctl status masha-osint nginx certbot.timer fail2ban
```

---

## 🎯 Fluxo de Desenvolvimento

### Desenvolvimento Local

```bash
# 1. Fazer mudanças localmente
vim app.py

# 2. Testar localmente
streamlit run app.py

# 3. Commitar
git add .
git commit -m "Add new feature"

# 4. Push (deploy automático!)
git push origin main
```

### Branches e Ambientes

**Produção (main):**
- Branch: `main`
- Deploy automático ao fazer push
- Domain: https://masha.freirecorporation.com

**Desenvolvimento (opcional):**
```bash
# Criar branch de desenvolvimento
git checkout -b develop

# Fazer mudanças
git add . && git commit -m "WIP: new feature"
git push origin develop

# Quando estiver pronto, merge para main
git checkout main
git merge develop
git push origin main  # <- Deploy automático!
```

---

## 🔐 Segurança

### Secrets no GitHub

- ✅ **Nunca** commite senhas ou API keys no código
- ✅ Use GitHub Secrets para credenciais sensíveis
- ✅ Secrets são criptografados e seguros
- ✅ Não aparecem nos logs públicos

### .env no VPS

- ✅ Arquivo `.env` tem permissão 600 (só o usuário pode ler)
- ✅ Não é commitado no git (está no `.gitignore`)
- ✅ Configurado durante o setup inicial
- ✅ Atualizado manualmente quando necessário

### Atualizações de API Keys

```bash
ssh root@72.62.166.247

# Editar .env
nano /opt/masha-osint/.env

# Atualizar keys
DEEPSEEK_API_KEY=novo-key
SERPAPI_KEY=novo-key

# Salvar (Ctrl+O, Enter, Ctrl+X)

# Reiniciar
systemctl restart masha-osint
```

---

## ✅ Checklist de Setup

- [ ] Script de inicialização executado no VPS
- [ ] Secrets configurados no GitHub
- [ ] Primeiro deployment manual testado
- [ ] Deployment automático testado com push
- [ ] Site acessível via HTTPS
- [ ] SSL configurado e válido
- [ ] Logs sendo gerados corretamente
- [ ] Monitoramento configurado

---

## 📚 Links Úteis

- **GitHub Actions**: https://github.com/freire19/Masha-OSINT/actions
- **Repositório**: https://github.com/freire19/Masha-OSINT
- **Site**: https://masha.freirecorporation.com
- **Documentação GitHub Actions**: https://docs.github.com/en/actions

---

**🎉 Pronto! Agora você tem deployment automático completo!**

Toda mudança que você fizer e der push, será automaticamente deployada no VPS. Zero trabalho manual! 🚀
