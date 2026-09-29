# Helpdesk Escolar — Instruções para Claude Code

## Remotes Git

| Remote | URL | Uso |
|--------|-----|-----|
| `helpdesk-gh` | `https://github.com/sendas/helpdesk-escolar.git` | **Produção** — o servidor Unraid faz `git pull` daqui |
| `origin` | `http://127.0.0.1:41059/git/sendas/SickGear` | Servidor local (não usado pelo servidor de produção) |

**REGRA CRÍTICA**: Sempre fazer push para `helpdesk-gh main` depois de cada commit:
```bash
git push helpdesk-gh HEAD:main
```
Sem este push, o servidor de produção nunca recebe o código novo.

## Servidor de Produção (Unraid)

- Localização do projeto: `/mnt/cache/appdata/helpdesk`
- Ficheiro compose: `docker-compose.unraid.yml`
- Base de dados: `/mnt/cache/appdata/helpdesk/data/tickets.db` (volume persistente — nunca apagado pelo build)

### Comandos de deploy no servidor:
```bash
cd /mnt/cache/appdata/helpdesk
docker compose -f docker-compose.unraid.yml exec -T backend python -m app.snapshot  # cópia consistente → data/tickets.db.bak-AAAAMMDD-HHMM
git pull
docker compose -f docker-compose.unraid.yml build --no-cache frontend backend
docker compose -f docker-compose.unraid.yml up -d
```

> A base de dados usa SQLite em modo WAL (desde v2.5.0): **não** copiar `tickets.db` com `cp` com a app a correr — usar `python -m app.snapshot` como acima.
> Além disso, a cada arranque o backend guarda uma cópia em `data/snapshots/` (mantém as 5 últimas).

> **IMPORTANTE**: O compose tem dois serviços separados — `frontend` e `backend`.
> Sempre rebuildar **ambos** com `build --no-cache frontend backend`.
> Se só se rebuildar o `frontend`, o backend fica com código antigo e os novos endpoints da API não ficam disponíveis.

## Credenciais GitHub (recuperação após reset de sessão)

Se o push para `helpdesk-gh` falhar com "Authentication failed", configurar o token:
```bash
git remote set-url helpdesk-gh https://<TOKEN>@github.com/sendas/helpdesk-escolar.git
```
O token é um GitHub Personal Access Token (classic) com scope `repo`.

## Versionamento

- **ATENÇÃO**: `TZ=Europe/Lisbon date` dentro do container pode mostrar data errada (data de criação do container). Verificar sempre a data real no contexto do sistema antes de bumpar versão.
- Ficheiro de versão: `frontend/src/utils/version.ts`
- Incrementar `APP_VERSION`, `APP_VERSION_DATE`, `APP_VERSION_TIME` e adicionar entrada em `RELEASE_NOTES`

## Stack

- **Backend**: FastAPI + SQLAlchemy async + SQLite (`aiosqlite`)
- **Frontend**: Quasar 2 / Vue 3 / TypeScript / Pinia
- **Deploy**: Docker + nginx (multi-stage build)
- **Auth**: LDAP on-premise + Azure AD / Entra ID → JWT interno
- **Migrações DB**: sem Alembic — usar `_add_missing_columns(conn)` em `main.py` com `PRAGMA table_info` + `ALTER TABLE ADD COLUMN`
- **Settings runtime**: `app_settings.json` em `/app/data/` via `_read_settings()` / `_write_settings()`

## Verificações antes de publicar

- Backend: `cd backend && pip install -r requirements-dev.txt && pytest` (testes em `backend/tests/`)
- Frontend: `cd frontend && npm run typecheck && npx quasar build`
- Cada commit de versão começa por `vX.Y.Z:` (ex.: `v2.7.0: ...`). O envio de tags git a partir desta sessão é
  bloqueado; para voltar atrás no servidor: `git log --oneline | grep "v2.6.0:"` → `git checkout <commit>` e rebuild
  (depois `git checkout main` para voltar a atualizar normalmente).

## Idioma

Toda a UI e mensagens em **português europeu** (pt-PT). Nunca usar inglês nas mensagens visíveis ao utilizador.
