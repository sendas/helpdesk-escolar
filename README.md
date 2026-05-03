# Helpdesk Escolar

Sistema de helpdesk para professores com autenticação via Active Directory (LDAP/LDAPS + Azure AD / Entra ID).

## Stack

| Camada | Tecnologia |
|--------|------------|
| Frontend | Quasar 2 (Vue 3 + TypeScript + Pinia) |
| Backend | Python 3.11 + FastAPI + SQLAlchemy async |
| Base de dados | SQLite (aiosqlite) → PostgreSQL-ready |
| Auth AD on-prem | `ldap3` |
| Auth Azure AD | `msal` + Microsoft Graph API |
| JWT interno | `python-jose` |
| Email | `fastapi-mail` + Jinja2 |
| Deploy | Docker + docker-compose |

## Arranque rápido (local)

```bash
cp .env.example .env
# Editar .env com as suas configurações
docker compose up --build -d
# Abrir http://localhost:85
```

O modo de demonstração (sem AD configurado) está sempre disponível no ecrã de login.

## Deployment

| Ambiente | Ficheiro | Porta |
|----------|----------|-------|
| Local / Windows | `docker-compose.yml` | :85 |
| Unraid NAS | `docker-compose.unraid.yml` | :85 |
| Linux + HTTPS | `docker-compose.prod.yml` + `Caddyfile` | 443 |

### Unraid

```bash
mkdir -p /mnt/cache/appdata/helpdesk
cp -r . /mnt/cache/appdata/helpdesk/
cd /mnt/cache/appdata/helpdesk
cp .env.example .env
# Editar .env
docker compose -f docker-compose.unraid.yml up --build -d
```

Os dados ficam guardados em `/mnt/cache/appdata/helpdesk/data/tickets.db`.

### Produção Linux (com HTTPS automático)

```bash
cp .env.prod.example .env.prod
# Editar DOMAIN, ACME_EMAIL, APP_SECRET_KEY, etc.
docker compose -f docker-compose.prod.yml --env-file .env.prod up --build -d
```

O Caddy obtém e renova o certificado Let's Encrypt automaticamente.

## Funcionalidades

- Tickets com estados: Aberto → Atribuído → Em Curso → Resolvido → Fechado
- 3 roles: Docente / Técnico / Administrador
- Autenticação LDAP two-step bind + Azure AD OAuth2
- Demo mode (sem AD configurado)
- Notificações por email (Jinja2 HTML templates)
- Painel de administração com estatísticas e gráficos (Chart.js)
- Backup / exportação JSON
- Suporte multi-escola
- Notas internas (visíveis apenas à equipa técnica)
- Modo escuro

## Migração Unraid → Servidor Linux

Apenas um ficheiro:

```bash
scp /mnt/cache/appdata/helpdesk/data/tickets.db user@servidor:/opt/helpdesk/data/
```

## Migração SQLite → PostgreSQL (futuro)

1. Substituir `aiosqlite` → `asyncpg` em `requirements.txt`
2. Alterar `DATABASE_URL` para `postgresql+asyncpg://user:pass@host/db`
3. Adicionar serviço `postgres` no `docker-compose.yml`
4. Zero alterações nos modelos
