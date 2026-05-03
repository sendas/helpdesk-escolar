# Guia de Migração — Unraid → Servidor Linux

> Instalaste no Unraid para testar e agora queres mover tudo para o servidor da escola com HTTPS? Este guia cobre exactamente isso — em menos de 15 minutos.

---

## O que vai acontecer

1. O servidor Linux recebe a aplicação e os dados do Unraid
2. O Unraid pode continuar a funcionar em paralelo durante a transição
3. Quando tudo estiver confirmado no Linux, apaga o Unraid

Não há perda de dados. Um único ficheiro (a base de dados) contém tudo.

---

## Passo 1 — Instala a aplicação no servidor Linux

Segue o **GUIA-LINUX.md** até ao Passo 5 (inicio da aplicação). Nessa altura já deves ter:
- A aplicação a correr em `https://helpdesk.queiro.pt`
- Uma base de dados vazia (sem tickets)

---

## Passo 2 — Copia a base de dados do Unraid

**No teu Mac**, abre o Terminal e corre:

```bash
scp root@IP-DO-NAS:/mnt/cache/appdata/helpdesk/data/tickets.db ~/Desktop/tickets.db
```

> Substitui `IP-DO-NAS` pelo IP do teu Unraid (ex: `192.168.1.50`)
> Vai pedir a password do Unraid (root).

O ficheiro `tickets.db` fica no teu Desktop — contém todos os tickets, utilizadores e categorias.

---

## Passo 3 — Para a aplicação no servidor Linux

```bash
ssh utilizador@helpdesk.queiro.pt
cd /opt/helpdesk
docker compose -f docker-compose.prod.yml --env-file .env.prod down
```

---

## Passo 4 — Copia a base de dados para o servidor Linux

**No teu Mac:**

```bash
scp ~/Desktop/tickets.db utilizador@helpdesk.queiro.pt:/tmp/tickets.db
```

**No servidor Linux:**

```bash
# Copia para o volume Docker onde o backend guarda os dados
docker run --rm \
  -v helpdesk_helpdesk_data:/data \
  -v /tmp:/tmp \
  alpine cp /tmp/tickets.db /data/tickets.db

echo "Feito!"
```

---

## Passo 5 — Reinicia a aplicação no Linux

```bash
cd /opt/helpdesk
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

Aguarda 30 segundos e abre `https://helpdesk.queiro.pt` — deves ver todos os dados do Unraid.

---

## Passo 6 — Verificar que tudo migrou

Entra com a conta de administrador e confirma:
- Tickets existentes estão presentes
- Utilizadores existentes aparecem em Utilizadores e permissões
- Categorias estão correctas

---

## Passo 7 — Funcionar em paralelo (opcional)

Se quiseres manter o Unraid activo temporariamente enquanto os utilizadores migram, podes ter os dois a funcionar ao mesmo tempo. Só precisas de adicionar ao `.env.prod` do servidor Linux:

```
EXTRA_ALLOWED_ORIGINS=http://192.168.1.50:85
```

Isto permite que pedidos do Unraid também funcionem durante a transição.

---

## Passo 8 — Desligar o Unraid (quando estiveres pronto)

No terminal do Unraid:

```bash
cd /mnt/cache/appdata/helpdesk
docker compose -f docker-compose.unraid.yml down
```

E remove a pasta se já não precisares:
```bash
rm -rf /mnt/cache/appdata/helpdesk
```

---

## Resumo visual

```
Unraid                          Servidor Linux
───────                         ──────────────
tickets.db  ──→ Mac Desktop ──→ /tmp/tickets.db ──→ volume Docker
                 (scp)               (scp)           (docker run cp)
```

---

*Dúvidas? Consulta os logs: `docker compose -f docker-compose.prod.yml logs backend`*
