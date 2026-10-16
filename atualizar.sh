#!/bin/sh
# Atualiza o helpdesk no servidor (Unraid): cópia de segurança, código novo, rebuild e arranque.
# Uso:  sh /mnt/cache/appdata/helpdesk/atualizar.sh
set -e
cd /mnt/cache/appdata/helpdesk
COMPOSE="docker compose -f docker-compose.unraid.yml"

echo "== 1/4 Cópia de segurança da base de dados"
$COMPOSE exec -T backend python -m app.snapshot || echo "(aviso: não foi possível fazer a cópia — o backend estava parado?)"

echo "== 2/4 Código novo"
git pull

echo "== 3/4 Rebuild (demora alguns minutos)"
$COMPOSE build --no-cache frontend backend

echo "== 4/4 Arranque"
$COMPOSE up -d
sleep 40

echo
echo "== Versão instalada:"
git log -1 --oneline
$COMPOSE ps
echo
echo "== Últimas linhas do backend:"
$COMPOSE logs --tail=15 backend
