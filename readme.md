# Python

Repositório de projetos Python. Atualmente contém:

- [`sfjwt/`](./sfjwt) — geração de certificado/chave RSA e autenticação no Salesforce via fluxo **JWT Bearer** (OAuth 2.0 JWT Bearer Flow).

---

## sfjwt

### Estrutura

```
sfjwt/
├── .gitignore
├── gen_cert.py         # gera server.key + server.crt
├── jwtgen.py           # monta, assina o JWT e troca por access token
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

### 1. Clonar e entrar na pasta

```bash
git clone https://github.com/andrelpcarvalho/Python.git
cd Python/sfjwt
```

### 2. Criar e ativar o ambiente virtual

```bash
python3 -m venv venv
source venv/bin/activate
```

O prompt do terminal deve passar a exibir `(venv)` no início. Confirme que está usando o Python da venv:

```bash
which python
```

Deve apontar para dentro de `sfjwt/venv/bin/python`. A venv precisa ser ativada (`source venv/bin/activate`) toda vez que você abrir um novo terminal.

### 3. Instalar as dependências

Com a venv ativa:

```bash
pip install -r requirements.txt
```

### 4. Gerar o certificado e a chave privada

```bash
python gen_cert.py
```

Isso cria `server.key` (chave privada, usada para assinar o JWT) e `server.crt` (certificado público). Faça upload do `server.crt` na Connected App do Salesforce, em **Setup > App Manager > [sua Connected App] > Edit > Use digital signatures**.

### 5. Configurar o `.env`

Crie um arquivo `.env` dentro de `sfjwt/` (nunca commitado) com:

```bash
SF_PRIVATE_KEY_PATH=server.key
SF_CONSUMER_KEY=seu_consumer_key_da_connected_app
SF_USERNAME=seu_usuario@org.com
SF_LOGIN_URL=https://login.salesforce.com
```

Use `https://login.salesforce.com` para produção/dev-edition ou `https://test.salesforce.com` para sandbox.

### 6. Gerar o token e autenticar

```bash
python jwtgen.py
```

O script monta o JWT assinado com `server.key`, troca por um access token no endpoint `/services/oauth2/token` do Salesforce e imprime a resposta (access token + instance URL).

### Problemas comuns

| Erro | Causa provável |
|---|---|
| `ModuleNotFoundError: No module named 'jwt'` ou `'dotenv'` | Venv não ativa, ou dependência não instalada. Rode `source venv/bin/activate` e `pip install -r requirements.txt`. |
| `zsh: command not found: pip` | Venv não está ativa. Ative com `source venv/bin/activate`. |
| `invalid_grant` na resposta do Salesforce | Certificado (`server.crt`) não corresponde à chave usada para assinar; usuário sem "Pre-Authorized" na Connected App; ou relógio do sistema dessincronizado (o `exp` do JWT fica inválido). |

### Segurança — importante

Este repositório é **público**. `server.key`, `.env` e `venv/` **nunca** devem ser commitados. Antes de qualquer `git push`, confirme que nada sensível está rastreado:

```bash
git ls-files | grep -E "\.key$|\.env$|venv/"
```

Se o comando não retornar nada, está seguro para subir. Caso algum desses arquivos já tenha sido commitado, revogue o certificado na Connected App do Salesforce, gere um novo par (`gen_cert.py`) e remova o arquivo do histórico do git (`git rm --cached` + reescrita de histórico com `git filter-repo` ou BFG, se necessário).

O `sfjwt/.gitignore` deve conter:

```
venv/
.env
*.key
*.crt
__pycache__/
*.pyc
```