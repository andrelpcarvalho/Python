#!/usr/bin/env bash
#
# setup.sh
# Cria o ambiente para rodar gen_cert.py e gen_jwt.py:
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
#   python gen_cert.py
#   # edite o .env, faça upload do server.crt na Connected App
#   python gen_jwt.py

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "==> Diretório do projeto: $PROJECT_DIR"

# ---------- requirements.txt ----------
if [ ! -f requirements.txt ]; then
  echo "==> Criando requirements.txt"
  cat > requirements.txt <<'EOF'
cffi==2.1.0
cryptography==49.0.0
pycparser==3.0
PyJWT==2.13.0
python-dotenv==1.2.2
EOF
else
  echo "==> requirements.txt já existe, mantendo"
fi

# ---------- .env ----------
if [ ! -f .env ]; then
  echo "==> Criando .env (preencha os valores antes de rodar)"
  cat > .env <<'EOF'
# Caminho da chave privada gerada por gen_cert.py
SF_PRIVATE_KEY_PATH=server.key

# Consumer Key da Connected App
SF_CONSUMER_KEY=

# Usuário de integração (precisa estar Pre-Authorized na Connected App)
SF_USERNAME=

# https://login.salesforce.com (produção/dev-edition) ou https://test.salesforce.com (sandbox)
SF_LOGIN_URL=https://login.salesforce.com
EOF
  echo "    -> Edite o .env e preencha SF_CONSUMER_KEY e SF_USERNAME"
else
  echo "==> .env já existe, mantendo (não sobrescrito)"
fi

# ---------- .gitignore ----------
if [ ! -f .gitignore ]; then
  echo "==> Criando .gitignore"
  cat > .gitignore <<'EOF'
venv/
.env
*.key
*.crt
__pycache__/
*.pyc
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
echo "    1. source venv/bin/activate"
echo "    2. python gen_cert.py   (gera server.key + server.crt)"
echo "    3. Faça upload do server.crt na Connected App do Salesforce"
echo "    4. Edite o .env com SF_CONSUMER_KEY e SF_USERNAME"
echo "    5. python gen_jwt.py    (gera e testa o access token)"