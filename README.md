# Helpdesk Escolar — Centro de Apoio Digital

> **⚠️ Direitos de autor / Copyright**
> Este software é propriedade exclusiva de **Pedro Sendas de Moura Pereira**.
> A sua utilização, reprodução ou distribuição sem autorização escrita prévia é expressamente proibida.
> Consulte o ficheiro [LICENSE](LICENSE) para mais informações.

Plataforma de pedidos de apoio informático para agrupamentos de escolas: docentes, não docentes e alunos pedem
ajuda, a equipa de apoio trata, acompanha e comunica — tudo num só sítio, com entrada através da conta Microsoft
institucional (Entra ID) ou do Active Directory da escola.

Versão atual: **v2.11.0** (ver `frontend/src/utils/version.ts` para as notas de cada versão).

## Stack

| Camada | Tecnologia |
|--------|------------|
| Frontend | Quasar 2 (Vue 3 + TypeScript + Pinia), Chart.js |
| Backend | Python 3.11 + FastAPI + SQLAlchemy async |
| Base de dados | SQLite em modo WAL (`aiosqlite`) — preparado para PostgreSQL |
| Autenticação | Azure AD / Entra ID (`msal` + Microsoft Graph) e LDAP/LDAPS on-premise (`ldap3`) → JWT interno (`PyJWT`) |
| Email | `fastapi-mail` + Jinja2; leitura de respostas por Microsoft Graph ou IMAP |
| Notificações | Email, push no browser (Web Push/VAPID), tempo real (SSE) |
| Deploy | Docker multi-stage + nginx; Caddy para HTTPS automático |

## Funcionalidades

### Para quem pede ajuda
- Criar pedidos com categoria, escola, prioridade, anexos, fotografias da câmara e imagens coladas
- Acompanhar o estado: Aberto → Atribuído → Em curso → A aguardar utilizador → Resolvido → Fechado
- Conversa no ticket com respostas, reações e **@menções**
- Avaliar o atendimento quando o pedido é resolvido
- Formulário "Não tenho acesso ao mail institucional" para docentes, não docentes e alunos (n.º de cartão, ano, turma, escola)
- Base de conhecimento, sugestões e chat
- Perfil próprio (`/perfil`): nome apresentado, telefone
- Preferências de notificação por tipo (`/notificacoes`)
- Janela de novidades com as alterações mais importantes

### Para a equipa de apoio
- Lista de tickets em vista de lista ou tabela, com filtros e paginação
- **Quadro** (Kanban) por estado, com filtro por tipo de pedido e vista para telemóvel
- Notas internas e **mensagens privadas** a uma ou várias pessoas (incluindo a Direção), agrupadas por conversa
- Respostas rápidas pré-definidas
- **Caixa de entrada** do email de apoio dentro da app: ler, responder, responder a todos, reencaminhar e eliminar
- Encaminhamento para a empresa de apoio externa com o resumo completo da conversa
- **Manutenção planeada**: tickets criados automaticamente (semanal, mensal, por período, anual)
- Lembretes, tickets atrasados e regras de encaminhamento automático
- Relatório mensal enviado por email à Direção

### Administração
- Papéis e permissões configuráveis (docente, não docente, técnico, secretaria, direção, administrador, …)
- Sincronização de utilizadores do Entra ID por unidade organizacional
- Multi-escola, categorias, grupos
- Estatísticas e gráficos (tickets criados e resolvidos por semana, por escola, por categoria)
- Cópias de segurança (JSON e ZIP) e reposição
- Modo escuro (incluindo "preto total" para ecrãs OLED)

### Segurança e dados
- Chaves secretas geradas automaticamente se estiverem fracas ou em falta
- Limite de tentativas de login, lista de tipos de ficheiro permitidos nos anexos
- Base de dados SQLite em modo WAL com `foreign_keys` ativas
- Cópia automática da base de dados a cada arranque (`data/snapshots/`, mantém as 5 últimas)
- Cópia consistente a pedido: `python -m app.snapshot`

## Arranque rápido (local)

```bash
cp .env.example .env
# Editar .env com as suas configurações
docker compose up --build -d
# Abrir http://localhost:85
```

## Deployment

| Ambiente | Ficheiro | Portas |
|----------|----------|--------|
| Local / Windows | `docker-compose.yml` | :85 |
| Unraid NAS | `docker-compose.unraid.yml` | :85 (frontend), :8089 (backend) |
| Linux + HTTPS | `docker-compose.prod.yml` + `Caddyfile` | 443 |

### Unraid — primeira instalação

```bash
mkdir -p /mnt/cache/appdata/helpdesk
cd /mnt/cache/appdata/helpdesk
git clone https://github.com/sendas/helpdesk-escolar.git .
cp app.env.unraid.example app.env
# Editar app.env
docker compose -f docker-compose.unraid.yml up --build -d
```

Os dados ficam em `/mnt/cache/appdata/helpdesk/data/` (`tickets.db`, anexos, definições, cópias de arranque).

### Unraid — atualizar para uma nova versão

```bash
cd /mnt/cache/appdata/helpdesk
docker compose -f docker-compose.unraid.yml exec -T backend python -m app.snapshot   # cópia → data/tickets.db.bak-AAAAMMDD-HHMM
git pull
docker compose -f docker-compose.unraid.yml build --no-cache frontend backend
docker compose -f docker-compose.unraid.yml up -d
```

> Rebuildar sempre **os dois** serviços (`frontend` e `backend`).
> Não copiar `tickets.db` com `cp` com a app a correr (modo WAL) — usar `python -m app.snapshot`.

**Voltar a uma versão anterior:** `git log --oneline | grep "v2.10.2:"` → `git checkout <commit>` e rebuild
(depois `git checkout main` para voltar a atualizar normalmente).

### Produção Linux (com HTTPS automático)

```bash
cp .env.prod.example .env.prod
# Editar DOMAIN, ACME_EMAIL, APP_SECRET_KEY, etc.
docker compose -f docker-compose.prod.yml --env-file .env.prod up --build -d
```

O Caddy obtém e renova o certificado Let's Encrypt automaticamente.

## Configuração Microsoft (Entra ID)

Registo de aplicação no Entra ID com as permissões Microsoft Graph:

| Permissão | Tipo | Para quê |
|-----------|------|----------|
| `User.Read` | Delegada | Login |
| `User.Read.All` | Aplicação | Sincronização de utilizadores |
| `Mail.ReadWrite` | Aplicação | Ler a caixa de entrada e as respostas por email |
| `Mail.Send` | Aplicação | Responder e reencaminhar a partir da Caixa de entrada |

Depois de adicionar permissões de aplicação, é preciso **conceder consentimento de administrador**.
As variáveis correspondentes estão em `app.env.unraid.example` (`AZURE_*`, `MAIL_REPLY_*`, `GRAPH_MAIL_USER`).

## Estatísticas para relatórios

```bash
docker compose -f docker-compose.unraid.yml exec -T backend python scripts/estatisticas.py 2026-09-01
```

Mostra os pedidos recebidos (média por dia e por dia útil), resolvidos, tempo médio de resolução, pedidos em aberto,
distribuição por escola e categoria e avaliações.

## Desenvolvimento

```bash
# Backend
cd backend && pip install -r requirements-dev.txt && pytest

# Frontend
cd frontend && npm ci && npm run typecheck && npx quasar build
```

- Migrações de base de dados sem Alembic: `_add_missing_columns()` em `backend/app/main.py`
- Definições em tempo de execução: `/app/data/app_settings.json`
- Toda a interface em português europeu (pt-PT)
- Cada versão: atualizar `frontend/src/utils/version.ts` e começar o commit por `vX.Y.Z:`

Guias detalhados em [`docs/`](docs): configuração local, Unraid, Linux e migração Unraid → Linux.

## Migração Unraid → Servidor Linux

```bash
docker compose -f docker-compose.unraid.yml exec -T backend python -m app.snapshot
scp /mnt/cache/appdata/helpdesk/data/tickets.db.bak-* user@servidor:/opt/helpdesk/data/tickets.db
scp -r /mnt/cache/appdata/helpdesk/data/uploads /mnt/cache/appdata/helpdesk/data/app_settings.json user@servidor:/opt/helpdesk/data/
```

## Migração SQLite → PostgreSQL (futuro)

1. Substituir `aiosqlite` → `asyncpg` em `requirements.txt`
2. Alterar `DATABASE_URL` para `postgresql+asyncpg://user:pass@host/db`
3. Adicionar serviço `postgres` no `docker-compose.yml`
4. Rever as migrações de `_add_missing_columns()` (usam `PRAGMA` do SQLite)

---

## Direitos de autor

Copyright © 2026 Pedro Sendas de Moura Pereira — Todos os direitos reservados.

Este software é propriedade exclusiva do autor. A sua utilização, reprodução, distribuição ou modificação, no todo ou em parte, sem autorização escrita prévia, é expressamente proibida. Consulte o ficheiro [LICENSE](LICENSE).
