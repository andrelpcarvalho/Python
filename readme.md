# salesforce-bulk-toolkit

Toolkit de scripts Python para operações em massa no Salesforce:

- [`sf-jwt/`](./sf-jwt) — gera certificado/chave RSA e monta um JWT assinado para o **JWT Bearer Flow**.
- [`bulk-api/`](./bulk-api) — consulta (`query.py`) e grava em massa (`update.py`) qualquer objeto do Salesforce via **Bulk API 2.0**, autenticado via **Client Credentials Flow**.
- [`split-large-csv/`](./split-large-csv) — divide um CSV grande em N arquivos menores, prontos para alimentar o `bulk-api`.

Cada pasta tem sua própria venv, `requirements.txt` e `.env` — são independentes entre si (exceto `bulk-api`, que unifica query e update num único ambiente, já que compartilham autenticação e formato de configuração).

---

## ⚠️ Segurança — leia antes de tudo

Este repositório é **público**. Nunca commite: `venv/`, `.env`, `*.key`, `*.crt`, `csv/`, `logs/`, `output/`. Cada pasta tem seu próprio `.gitignore`, e agora também existe um **`.gitignore` na raiz** cobrindo esses padrões globalmente — isso corrige um problema real: um `.env` chegou a ser commitado na raiz do repo porque não havia proteção nesse nível (só dentro das subpastas). Nenhuma credencial vazou nesse incidente (o `.env` em questão só tinha parâmetros de query, sem client secret), mas o princípio vale: a partir de agora, rode os scripts sempre de dentro da pasta do projeto, nunca da raiz.

Antes de qualquer `git push`, confirme que nada sensível está rastreado:

```bash
git ls-files | grep -E "\.key$|\.crt$|\.env$|venv/"
```

Se não retornar nada, está seguro. Se algo já foi commitado por engano, remova do tracking (`git rm --cached arquivo`) e, se era credencial de verdade (não é o caso aqui), revogue e gere uma nova.

---

## sf-jwt

### Estrutura

```
sf-jwt/
├── .gitignore
├── gen_cert.py      # gera salesforce.key + connectedAppCertificate.crt
├── gen_jwt.py        # monta o JWT, assina, e troca pelo access token via /services/oauth2/token
├── requirements.txt
└── setup.sh          # cria venv, requirements.txt e .env

# gerados localmente, não versionados:
├── venv/
├── .env
├── salesforce.key
└── connectedAppCertificate.crt
```

### Pré-requisitos

- Python 3.9+
- Connected App no Salesforce com "Use digital signatures" (usando o `connectedAppCertificate.crt` gerado aqui) e "Enable OAuth Settings" habilitados, com o usuário `SF_USERNAME` Pre-Authorized.

### Setup e uso

```bash
cd sf-jwt
chmod +x setup.sh
./setup.sh

source venv/bin/activate
python gen_cert.py
# -> faça upload de connectedAppCertificate.crt na Connected App

# edite o .env com SF_CONSUMER_KEY e SF_USERNAME
python gen_jwt.py
# -> imprime access_token e instance_url, prontos para uso
```

---

## bulk-api

Unifica os antigos `bulkApi_Query` e `bulkApi_Update` numa pasta só — eles compartilhavam o mesmo `auth.py` (Client Credentials Flow) e o mesmo objeto-alvo na prática, então faz mais sentido um único venv/`.env`/setup.

### Estrutura

```
bulk-api/
├── .gitignore
├── auth.py                # autenticação (Client Credentials Flow) — compartilhado
├── configure_query.py      # wizard interativo: objeto, campos, WHERE, ORDER BY, LIMIT
├── configure_update.py     # wizard interativo: objeto, operação, external ID field
├── field_mapping.py        # mapeia colunas do CSV -> campos reais da API (via Describe)
├── query.py                 # executa a query (Bulk API 2.0 - jobs/query)
├── update.py                 # executa insert/update/upsert/delete (Bulk API 2.0 - jobs/ingest)
├── run_query.py              # configure_query.py + query.py num comando só
├── run_update.py             # configure_update.py + field_mapping.py (opcional) + update.py
├── requirements.txt
└── setup.sh

# gerados localmente, não versionados:
├── venv/
├── .env
├── csv/                     # CSVs de entrada pro update (ex: vindos do split-large-csv)
├── output/                  # CSV de saída da query
├── header_mapping.json      # gerado por field_mapping.py
└── logs/                    # log de execução + resultados de sucesso/erro por job
```

### Pré-requisitos

- Python 3.9+
- Connected App no Salesforce com "Enable Client Credentials Flow" habilitado e "Run As" apontando pro usuário de integração, com permissão no objeto/operação que você for usar.

### Setup

```bash
cd bulk-api
chmod +x setup.sh
./setup.sh
```

Preencha pelo menos `SF_CLIENT_ID`, `SF_CLIENT_SECRET` e `SF_LOGIN_URL` (My Domain, ex: `https://suaorg.my.salesforce.com`) no `.env`. O resto pode ser preenchido na mão ou de forma guiada pelos comandos abaixo.

### Uso — consultar (query)

```bash
source venv/bin/activate
python run_query.py
```

Pergunta objeto, campos, `WHERE`/`ORDER BY`/`LIMIT` (cada um opcional, com pergunta sim/não), roda a query e salva o CSV em `SF_OUTPUT_PATH`.

### Uso — atualizar em massa (insert/update/upsert/delete)

```bash
source venv/bin/activate
python run_update.py
```

Pergunta objeto, operação e `CSV_DIR`; pergunta se as colunas do CSV batem com a API (se não, chama `field_mapping.py` automaticamente); processa todos os CSVs de `CSV_DIR` em ordem numérica, um job por vez, parando a sequência se algum tiver falha.

Cada peça também roda isolada, se preferir: `python configure_query.py`, `python query.py`, `python configure_update.py`, `python field_mapping.py`, `python update.py`.

---

## split-large-csv

### Estrutura

```
split-large-csv/
├── .gitignore
├── requirements.txt
├── setup.sh
└── split_csv.py
```

### Setup e uso

```bash
cd split-large-csv
chmod +x setup.sh
./setup.sh

source venv/bin/activate
# edite o .env: INPUT_FILE, OUTPUT_DIR, OUTPUT_PREFIX, MAX_ROWS
python split_csv.py
```

Fluxo típico: aponte `OUTPUT_DIR` direto pra `bulk-api/csv/`, depois rode `python run_update.py` no `bulk-api`.

---

## Fluxo ponta a ponta (exemplo: update de 23M registros)

```bash
# 1. Dividir o CSV de origem em partes de 1M linhas
cd split-large-csv && ./setup.sh
source venv/bin/activate
# .env: OUTPUT_DIR=../bulk-api/csv
python split_csv.py
deactivate

# 2. Configurar e rodar o update em massa
cd ../bulk-api && ./setup.sh
source venv/bin/activate
python run_update.py
```