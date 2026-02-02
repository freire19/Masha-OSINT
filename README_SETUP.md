# ⚡ Setup Automação Completa - 3 Passos

## 🎯 Objetivo

Depois destes 3 passos, **NUNCA MAIS** você precisará fazer deployment manual.
Todo `git push` fará deploy automático! 🚀

---

## 📋 Passo 1: Inicializar VPS (UMA VEZ)

Cole este comando no seu terminal:

```bash
ssh root@72.62.166.247 'bash -s' < <(curl -fsSL https://raw.githubusercontent.com/freire19/Masha-OSINT/main/init-vps-once.sh)
```

**Senha:** `EusouISD92@#`

O script vai pedir:
- **Domain:** `masha.freirecorporation.com`
- **Email:** Seu email (para SSL)
- **DeepSeek API Key:** (cole sua key)
- **SerpAPI Key:** (cole sua key)
- **Web Password:** (senha segura para o site)

---

## 🔐 Passo 2: Configurar GitHub Secrets

### 2.1 - Acesse:
https://github.com/freire19/Masha-OSINT/settings/secrets/actions

### 2.2 - Adicione 3 secrets (clique em "New repository secret" para cada):

**Secret 1:**
- Name: `VPS_HOST`
- Value: `72.62.166.247`

**Secret 2:**
- Name: `VPS_USER`
- Value: `root`

**Secret 3:**
- Name: `VPS_PASSWORD`
- Value: `EusouISD92@#`

---

## 🚀 Passo 3: Adicionar Workflow

Cole estes comandos no terminal:

```bash
cd /home/freire/Documents/MeusProjetos/Masha-OSINT

# Adicionar e commitar o workflow
git add .github/workflows/deploy.yml

git commit -m "Add GitHub Actions workflow for auto-deployment

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# Push (se pedir password do GitHub, use seu Personal Access Token)
git push origin main
```

**Se der erro de permissão:**
Você precisa criar um Personal Access Token com scope `workflow`:
1. Acesse: https://github.com/settings/tokens
2. Clique em "Generate new token" → "Classic"
3. Marque: `repo` e `workflow`
4. Gere e copie o token
5. Use o token como senha quando der `git push`

---

## ✅ Pronto!

Agora teste o deploy automático:

```bash
# Faça qualquer mudança
echo "# Test" >> README.md

# Commit e push
git add .
git commit -m "Test auto-deployment"
git push origin main
```

**O que acontece:**
1. GitHub detecta o push
2. Executa o workflow automaticamente
3. Conecta no VPS
4. Atualiza o código
5. Reinicia o serviço
6. Site atualizado! 🎉

Veja o progresso em:
https://github.com/freire19/Masha-OSINT/actions

---

## 🎯 Resultado Final

**Antes:** 😩
```
1. SSH no VPS
2. git pull
3. pip install
4. systemctl restart
5. Verificar logs
6. Testar site
```

**Depois:** 😎
```
git push
```

**FIM!** O resto é automático! 🚀

---

## 📚 Documentação Completa

- **CI/CD Guide:** [CI-CD.md](CI-CD.md)
- **Manual Deployment:** [DEPLOY_MANUAL.md](DEPLOY_MANUAL.md)
- **Full Docs:** [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

---

## ❓ Problemas?

### "Workflow não executou"
→ Verifique que os 3 secrets estão configurados corretamente

### "Deployment falhou"
→ Veja os logs em: https://github.com/freire19/Masha-OSINT/actions

### "Serviço não inicia"
```bash
ssh root@72.62.166.247
journalctl -u masha-osint -n 50
```

---

**Qualquer dúvida, veja [CI-CD.md](CI-CD.md) para documentação completa!**
