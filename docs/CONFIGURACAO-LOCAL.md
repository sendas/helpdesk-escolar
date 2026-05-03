# Configuracao local

Este projeto pode correr de duas formas: com Docker Compose, que e a opcao prevista no README, ou com backend/frontend separados durante desenvolvimento.

## Opcao recomendada: Docker Compose

1. Instalar Docker Desktop.
2. Confirmar no terminal:

```bash
docker --version
docker compose version
```

3. Na raiz do repositorio:

```bash
cp .env.example .env
```

4. Para ambiente local sem LDAP, Azure AD e email reais, usar estes valores no `.env`:

```dotenv
APP_DEBUG=true
FRONTEND_URL=http://localhost:85
LDAP_ENABLED=false
AZURE_AD_ENABLED=false
MAIL_SUPPRESS_SEND=true
```

5. Arrancar:

```bash
docker compose up --build -d
```

6. Abrir:

```text
http://localhost:85
```

O login de demonstracao nao precisa de password. No ecra de login, escolhe o perfil `Docente`, `Tecnico` ou `Administrador` e entra em modo demo.

## Desenvolvimento sem Docker

### Backend

Requer Python 3.11 ou superior.

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8089 --reload
```

Health check:

```bash
curl http://localhost:8089/health
```

### Frontend

Requer Node 18 ou superior e npm.

```bash
cd frontend
npm install
npm run dev
```

Abrir:

```text
http://localhost:9000
```

O `quasar.config.js` ja faz proxy de `/api` para `http://localhost:8089`.

## Notas para producao

Antes de producao:

- Trocar `APP_SECRET_KEY` por uma chave longa e aleatoria.
- Configurar LDAP ou Azure AD com dados reais.
- Configurar SMTP se quiser notificacoes por email.
- Usar `docker-compose.prod.yml` e `.env.prod` para Linux com HTTPS via Caddy.
