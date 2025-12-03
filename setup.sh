#!/usr/bin/env bash
# ============================================================
#  Masha OSINT – Setup de Ambiente (Ubuntu/Debian)
#  Cria venv, instala dependências e prepara o .env
# ============================================================

set -euo pipefail

PROJECT_ROOT="$(pwd)"
VENV_DIR="${PROJECT_ROOT}/venv"

echo "==========================================="
echo "   MASHA OSINT - SETUP DE AMBIENTE"
echo "==========================================="

# ------------------------------------------------------------
# 1) Verificação básica de estrutura
# ------------------------------------------------------------
if [ ! -f "${PROJECT_ROOT}/main.py" ]; then
  echo "⚠️  Aviso: main.py não encontrado na pasta atual."
  echo "   Certifique-se de rodar este script na raiz do projeto Masha-OSINT."
fi

if [ ! -d "${PROJECT_ROOT}/src" ]; then
  echo "⚠️  Aviso: pasta src/ não encontrada."
  echo "   Estrutura esperada: src/agents, src/tools, src/utils, etc."
fi

# ------------------------------------------------------------
# 2) Detectar Python
# ------------------------------------------------------------
if command -v python3 &>/dev/null; then
  PYTHON_BIN="python3"
elif command -v python &>/dev/null; then
  PYTHON_BIN="python"
else
  echo "❌ Nenhum interpretador Python encontrado (python3 ou python)."
  echo "   Instale com: sudo apt install python3 python3-venv"
  exit 1
fi

echo "➡️  Usando Python: ${PYTHON_BIN}"

# ------------------------------------------------------------
# 3) Criar (ou reutilizar) o ambiente virtual
# ------------------------------------------------------------
if [ -d "${VENV_DIR}" ]; then
  echo "✅ Ambiente virtual já existe em: ${VENV_DIR}"
else
  echo "🔧 Criando ambiente virtual em: ${VENV_DIR}"
  ${PYTHON_BIN} -m venv "${VENV_DIR}"
fi

# Ativar venv
# shellcheck disable=SC1090
source "${VENV_DIR}/bin/activate"

echo "✅ venv ativado: $(which python)"

# ------------------------------------------------------------
# 4) Atualizar pip dentro do venv
# ------------------------------------------------------------
echo "🔧 Atualizando pip..."
python -m pip install --upgrade pip

# ------------------------------------------------------------
# 5) Instalar dependências necessárias
# ------------------------------------------------------------
echo "🔧 Instalando dependências da Masha OSINT..."

pip install \
  curl_cffi \
  requests \
  beautifulsoup4 \
  pdfplumber \
  pandas \
  openpyxl \
  python-dotenv \
  colorama \
  openai

echo "✅ Dependências instaladas."

# ------------------------------------------------------------
# 6) Gerar/atualizar requirements.txt
# ------------------------------------------------------------
echo "🔧 Gerando requirements.txt..."
pip freeze > requirements.txt
echo "✅ requirements.txt atualizado."

# ------------------------------------------------------------
# 7) Criar .env de exemplo (se não existir)
# ------------------------------------------------------------
ENV_FILE="${PROJECT_ROOT}/.env"

if [ -f "${ENV_FILE}" ]; then
  echo "✅ .env já existe, não será sobrescrito."
else
  echo "🔧 Criando .env de exemplo..."

  cat > "${ENV_FILE}" <<EOF
# ============================================================
#  CONFIGURAÇÕES DA MASHA OSINT
# ============================================================

# Chave da API DeepSeek (modelo deepseek-reasoner)
DEEPSEEK_API_KEY=COLOQUE_SUA_CHAVE_AQUI

# Chave da API SerpAPI (para busca no Google)
SERPAPI_KEY=COLOQUE_SUA_CHAVE_AQUI

# Opcional: idioma/região padrão da busca
# Ex: us/en, br/pt-br
DEFAULT_SEARCH_COUNTRY=us
DEFAULT_SEARCH_LANG=en
EOF

  echo "✅ .env criado. Edite com: nano .env ou micro .env"
fi

# ------------------------------------------------------------
# 8) Resumo final
# ------------------------------------------------------------
echo ""
echo "==========================================="
echo "      SETUP CONCLUÍDO COM SUCESSO ✅"
echo "==========================================="
echo ""
echo "➡ Para usar a Masha OSINT agora:"
echo "   cd ${PROJECT_ROOT}"
echo "   source venv/bin/activate"
echo "   python3 main.py"
echo ""
echo "⚠️ Não esqueça de editar o arquivo .env e colocar:"
echo "   - DEEPSEEK_API_KEY"
echo "   - SERPAPI_KEY"
echo ""
