# Python

Repositório de projetos Python. Atualmente contém:

- [`sfjwt/`](./sfjwt) — geração de certificado/chave RSA e autenticação no Salesforce via **JWT Bearer Flow** (OAuth 2.0).
- [`bulkApi/`](./bulkApi) — atualização em massa de registros do Salesforce via **Bulk API 2.0**, autenticado via **Client Credentials Flow**, processando múltiplos CSVs em sequência.
- [`splitLargeCsv/`](./splitLargeCsv) — divide um CSV grande em N arquivos menores, prontos para alimentar o `bulkApi`.

Cada projeto tem sua própria venv, `requirements.txt` e `.env` — são independentes entre si.

---

## sfjwt

### Estrutura

```
sfjwt/
├── .gitignore
├── gen_cert.py         # gera server.key + server.crt
├── gen_jwt.py           # monta, assina o JWT e troca por access token
└── requirements.txt    # dependências do projeto

# gerados localmente, não versionados:
├── venv/               # ambiente virtual
├── .env                # variáveis sensíveis
├── server.key           # chave privada
└── server.crt           # certificado público
```

### Pré-requisitos

- Python 3.9+
- Uma Connected App configurada no Salesforce com:
  - "Use digital signatures" habilitado, com o `server.crt` gerado por este projeto
  - "Enable OAuth Settings" habilitado
  - O usuário (`SF_USERNAME`) com acesso "Pre-Authorized" à Connected App

### Setup (sem script automático — venv manual)

```bash
cd sfjwt
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Confirme que está usando o Python da venv: `which python` deve apontar para dentro de `sfjwt/venv/bin/python`. A venv precisa ser reativada (`source venv/bin/activate`) toda vez que você abrir um novo terminal.

### Uso

```bash
# 1. Gerar certificado e chave privada
python gen_cert.py
# -> cria server.key e server.crt. Faça upload do server.crt na Connected App
#    do Salesforce, em Setup > App Manager > [sua Connected App] > Edit > Use digital signatures.

# 2. Criar o .env dentro de sfjwt/ (nunca commitado)
cat > .env <<'EOF'
SF_PRIVATE_KEY_PATH=server.key
SF_CONSUMER_KEY=seu_consumer_key_da_connected_app
SF_USERNAME=seu_usuario@org.com
SF_LOGIN_URL=https://login.salesforce.com
EOF
# Use https://login.salesforce.com para produção/dev-edition
# ou https://test.salesforce.com para sandbox.

# 3. Gerar o token e autenticar
python gen_jwt.py
```

O `gen_jwt.py` monta o JWT assinado com `server.key`, troca por um access token no endpoint `/services/oauth2/token` do Salesforce e imprime a resposta (access token + instance URL).

### Problemas comuns

| Erro | Causa provável |
|---|---|
| `ModuleNotFoundError: No module named 'jwt'` ou `'dotenv'` | Venv não ativa, ou dependência não instalada. Rode `source venv/bin/activate` e `pip install -r requirements.txt`. |
| `zsh: command not found: pip` | Venv não está ativa. Ative com `source venv/bin/activate`. |
| `invalid_grant` na resposta do Salesforce | Certificado (`server.crt`) não corresponde à chave usada para assinar; usuário sem "Pre-Authorized" na Connected App; ou relógio do sistema dessincronizado (o `exp` do JWT fica inválido). |

---

## bulkApi

### Estrutura

```
bulkApi/
├── .gitignore
├── auth.py                    # autenticação via Client Credentials Flow
├── bulk_update_account.py     # pipeline de update em massa (Bulk API 2.0)
├── requirements.txt
└── setup.sh                    # cria venv, requirements.txt e .env automaticamente

# gerados localmente, não versionados:
├── venv/
├── .env
├── csv/                        # arquivos de entrada (23 CSVs, ex: parte_1.csv...parte_23.csv)
└── logs/                        # logs de execução + resultados de sucesso/erro por job
```

### Pré-requisitos

- Python 3.9+
- Connected App no Salesforce com "Enable Client Credentials Flow" habilitado e "Run As" apontando para o usuário de integração com permissão de editar o objeto alvo (Account).

### Setup (automático)

```bash
cd bulkApi
chmod +x setup.sh
./setup.sh
```

Isso cria `venv/`, instala `requests` e `python-dotenv`, gera o `.env` em branco e o `.gitignore`. Edite o `.env` com suas credenciais:

```
SF_CLIENT_ID=
SF_CLIENT_SECRET=
SF_LOGIN_URL=https://suaorg.my.salesforce.com   # My Domain, não login.salesforce.com
SF_API_VERSION=v61.0
CSV_DIR=./csv
```

### Uso

```bash
source venv/bin/activate
set -a && source .env && set +a
python bulk_update_account.py
```

O script reautentica (via `auth.py`) antes de cada arquivo, processa os CSVs de `CSV_DIR` em ordem numérica, e para a sequência inteira se algum job tiver registros com falha (`stop_on_error=True` em `CONFIG`).

---

## splitLargeCsv

### Estrutura

```
splitLargeCsv/
├── .gitignore
├── requirements.txt
├── setup.sh              # cria venv, requirements.txt e .env automaticamente
└── split_csv.py           # divide o CSV de origem em N partes

# gerados localmente, não versionados:
├── venv/
└── .env
```

### Setup (automático)

```bash
cd splitLargeCsv
chmod +x setup.sh
./setup.sh
```

Edite o `.env` gerado:

```
INPUT_FILE=seu_arquivo.csv      # CSV de origem
OUTPUT_DIR=./csv                # pasta de saída (pode apontar direto para bulkApi/csv)
OUTPUT_PREFIX=parte             # gera parte_1.csv, parte_2.csv, ...
MAX_ROWS=1000000                # linhas por arquivo
```

### Uso

```bash
source venv/bin/activate
python split_csv.py
```

Fluxo típico: gere os CSVs aqui apontando `OUTPUT_DIR` para a pasta `csv/` do `bulkApi`, depois rode o `bulkApi` para subir tudo em sequência.

---

## Segurança — importante

Este repositório é **público**. Nunca commite: `venv/`, `.env`, `server.key`, `server.crt`, `csv/`, `logs/`. Cada projeto já tem `.gitignore` cobrindo isso. Antes de qualquer `git push`, confirme que nada sensível está rastreado:

```bash
git ls-files | grep -E "\.key$|\.env$|venv/"
```

Se o comando não retornar nada, está seguro para subir. Caso algum desses arquivos já tenha sido commitado, revogue a credencial correspondente (certificado na Connected App, ou Client Secret) e remova o arquivo do histórico do git (`git rm --cached` + reescrita de histórico com `git filter-repo` ou BFG, se necessário).