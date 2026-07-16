#!/usr/bin/env bash
#
# setup.sh
# Cria o ambiente para rodar bulk_query.py:
#   - venv Python
#   - requirements.txt
#   - .env (template, com valores em branco para você preencher)
#
# Uso:
#   chmod +x setup.sh
#   ./setup.sh
#
# Depois, pra rodar:
#   source venv/bin/activate
#   set -a && source .env && set +a
#   python bulk_query.py

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

# Objeto a consultar, ex: Account
SF_OBJECT=

# Campos separados por vírgula, ex: Id,Name,BillingCity
SF_FIELDS=

# Cláusula WHERE opcional (sem o "WHERE"), ex: CreatedDate = TODAY
SF_WHERE=

# ORDER BY opcional (sem o "ORDER BY"), ex: CreatedDate DESC
SF_ORDER_BY=

# LIMIT opcional (sem o "LIMIT"), ex: 1000
SF_LIMIT=

# Caminho do CSV de saída
SF_OUTPUT_PATH=./output/resultado.csv
EOF
  echo "    -> Edite o .env e preencha SF_CLIENT_ID, SF_CLIENT_SECRET, SF_LOGIN_URL, SF_OBJECT e SF_FIELDS"
else
  echo "==> .env já existe, mantendo (não sobrescrito)"
fi

# ---------- .gitignore ----------
if [ ! -f .gitignore ]; then
  echo "==> Criando .gitignore"
  cat > .gitignore <<'EOF'
.env
venv/
logs/
output/
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
echo "    1. Edite o .env com suas credenciais e a query desejada"
echo "    2. source venv/bin/activate"
echo "    3. set -a && source .env && set +a"
echo "    4. python bulk_query.py"