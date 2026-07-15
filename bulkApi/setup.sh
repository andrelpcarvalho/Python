#!/usr/bin/env bash
#
# setup.sh
# Cria o ambiente para rodar bulk_update_account.py:
#   - venv Python
#   - requirements.txt
#   - .env (template, com valores em branco para você preencher)
#
# Uso:
#   chmod +x setup.sh
#   ./setup.sh
#
# Depois, pra rodar o script principal:
#   source venv/bin/activate
#   set -a && source .env && set +a
#   python bulk_update_account.py

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "==> Diretório do projeto: $PROJECT_DIR"

# ---------- requirements.txt ----------
if [ ! -f requirements.txt ]; then
  echo "==> Criando requirements.txt"
  cat > requirements.txt <<'EOF'
requests>=2.31.0
python-dotenv>=1.0.0
EOF
else
  echo "==> requirements.txt já existe, mantendo"
fi

# ---------- .env ----------
if [ ! -f .env ]; then
  echo "==> Criando .env (preencha os valores antes de rodar)"
  cat > .env <<'EOF'
# Consumer Key do Connected App
SF_CLIENT_ID=

# Consumer Secret do Connected App
SF_CLIENT_SECRET=

# My Domain da org, ex: https://suaorg.my.salesforce.com
SF_LOGIN_URL=

# Versão da API
SF_API_VERSION=v61.0

# Diretório com os 23 CSVs (nomeados 01_...csv, 02_...csv, etc.)
CSV_DIR=./csv
EOF
  echo "    -> Edite o .env e preencha SF_CLIENT_ID, SF_CLIENT_SECRET e SF_LOGIN_URL"
else
  echo "==> .env já existe, mantendo (não sobrescrito)"
fi

# ---------- .gitignore (evita subir segredo por acidente) ----------
if [ ! -f .gitignore ]; then
  echo "==> Criando .gitignore"
  cat > .gitignore <<'EOF'
.env
venv/
logs/
csv/
EOF
fi

# ---------- venv ----------
if [ ! -d venv ]; then
  echo "==> Criando venv"
  python3 -m venv venv
else
  echo "==> venv já existe, mantendo"
fi

echo "==> Instalando dependências dentro do venv"
./venv/bin/pip install --upgrade pip --quiet
./venv/bin/pip install -r requirements.txt --quiet

echo ""
echo "==> Setup concluído."
echo "    1. Edite o .env com suas credenciais"
echo "    2. source venv/bin/activate"
echo "    3. set -a && source .env && set +a"
echo "    4. python bulk_update_account.py"