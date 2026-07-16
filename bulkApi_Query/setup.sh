#!/usr/bin/env bash
#
# setup.sh
#
# Prepara o ambiente do projeto: cria venv, instala as
# dependencias do requirements.txt e copia o .env.example
# pra .env (se ainda nao existir).
#
# ── USO ──────────────────────────────────────────────────────
# chmod +x setup.sh
# ./setup.sh

set -e

VENV_DIR=".venv"

echo "== Setup do projeto =="

if [ ! -d "$VENV_DIR" ]; then
    echo "Criando virtualenv em $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
else
    echo "Virtualenv ja existe em $VENV_DIR, pulando criacao."
fi

echo "Ativando virtualenv..."
source "$VENV_DIR/bin/activate"

echo "Instalando dependencias..."
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo ".env criado a partir de .env.example. Preencha SF_CLIENT_ID, SF_CLIENT_SECRET e SF_LOGIN_URL."
    else
        echo "Aviso: .env.example nao encontrado, .env nao foi criado."
    fi
else
    echo ".env ja existe, mantido como esta."
fi

echo ""
echo "Setup concluido."
echo "Proximos passos:"
echo "  1. source $VENV_DIR/bin/activate"
echo "  2. Preencher credenciais no .env"
echo "  3. python config.py              # define objeto/campos/output"
echo "  4. python bulk_query_account.py  # roda a query"