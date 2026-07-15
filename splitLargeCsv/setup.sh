#!/usr/bin/env bash
#
# setup.sh
# Cria o ambiente para rodar split_csv.py:
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
#   python split_csv.py

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "==> Diretório do projeto: $PROJECT_DIR"

# ---------- requirements.txt ----------
if [ ! -f requirements.txt ]; then
  echo "==> Criando requirements.txt"
  cat > requirements.txt <<'EOF'
python-dotenv>=1.0.0
EOF
else
  echo "==> requirements.txt já existe, mantendo"
fi

# ---------- .env ----------
if [ ! -f .env ]; then
  echo "==> Criando .env (preencha os valores antes de rodar)"
  cat > .env <<'EOF'
# Caminho do CSV de origem (23M linhas)
INPUT_FILE=seu_arquivo.csv

# Pasta onde os arquivos divididos serão salvos
OUTPUT_DIR=./csv

# Prefixo dos arquivos gerados -> parte_1.csv, parte_2.csv, ...
OUTPUT_PREFIX=parte

# Linhas por arquivo
MAX_ROWS=1000000
EOF
  echo "    -> Edite o .env e preencha INPUT_FILE"
else
  echo "==> .env já existe, mantendo (não sobrescrito)"
fi

# ---------- .gitignore ----------
if [ ! -f .gitignore ]; then
  echo "==> Criando .gitignore"
  cat > .gitignore <<'EOF'
.env
venv/
csv/
*.csv
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
echo "    1. Edite o .env com o caminho do seu CSV de origem"
echo "    2. source venv/bin/activate"
echo "    3. python split_csv.py"