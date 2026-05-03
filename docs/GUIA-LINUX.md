# Guia de Instalação — Servidor Linux (produção com HTTPS)

> **Para quem é este guia?** Para instalar o sistema num servidor Linux com um domínio próprio (ex: `helpdesk.queiro.pt`), com certificado SSL automático. Não precisas de comprar certificados — o Caddy trata de tudo.

---

## O que vais precisar

- Um servidor Linux (Ubuntu 22.04 / Debian 12 recomendado)
- Acesso SSH ao servidor
- Um domínio apontado para o IP do servidor (ex: `helpdesk.queiro.pt → 185.x.x.x`)
- Portas 80 e 443 abertas no firewall do servidor
- Docker instalado no servidor

---

## Parte 1 — Verificar pré-requisitos

Liga ao servidor via SSH:

```bash
ssh utilizador@helpdesk.queiro.pt
```

Verifica se o Docker está instalado:

```bash
docker --version
docker compose version
```

Se não estiver instalado, instala com:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Faz logout e login novamente para o grupo docker ficar activo
```

Verifica se o domínio aponta para este servidor:

```bash
curl -s ifconfig.me   # mostra o IP do servidor
# Compara com o IP do registo DNS do teu domínio
```

> Se o IP não corresponder, vai ao painel DNS do teu domínio (Cloudflare, GoDaddy, etc.) e cria um registo A: `helpdesk.queiro.pt → IP-DO-SERVIDOR`
> Pode demorar até 30 minutos a propagar.

---

## Parte 2 — Descarregar a aplicação

```bash
# Cria a pasta da aplicação
sudo mkdir -p /opt/helpdesk
sudo chown $USER:$USER /opt/helpdesk

# Descarrega o código
cd /opt/helpdesk
git clone https://github.com/sendas/helpdesk-escolar.git .
```

Verifica:
```bash
ls
```
Deves ver: `backend  frontend  docker-compose.prod.yml  Caddyfile  .env.prod.example`

---

## Parte 3 — Criar o ficheiro de configuração de produção

```bash
cp .env.prod.example .env.prod
nano .env.prod
```

**Edita estas linhas:**

```bash
# O teu domínio
DOMAIN=helpdesk.queiro.pt

# Email para receber alertas do certificado SSL
ACME_EMAIL=ti@queiro.pt

# Chave secreta — OBRIGATÓRIO MUDAR — gera uma com o comando abaixo
APP_SECRET_KEY=cola-aqui-a-chave-gerada

# URL da aplicação (com https://)
FRONTEND_URL=https://helpdesk.queiro.pt
```

**Gera a chave secreta** (copia o resultado e cola no APP_SECRET_KEY acima):

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**LDAP (se tiveres Active Directory na escola):**

```bash
LDAP_ENABLED=true
LDAP_SERVER=ldaps://dc.escola.local
LDAP_PORT=636
LDAP_BIND_DN=cn=svc_tickets,ou=ServiceAccounts,dc=escola,dc=local
LDAP_BIND_PASSWORD=password-da-conta-de-servico
LDAP_BASE_DN=ou=Staff,dc=escola,dc=local
LDAP_ADMIN_GROUP=CN=TI-Suporte,ou=Groups,dc=escola,dc=local
```

**Email (para notificações automáticas):**

```bash
MAIL_SERVER=smtp.queiro.pt
MAIL_PORT=587
MAIL_FROM=tickets@queiro.pt
MAIL_USERNAME=tickets@queiro.pt
MAIL_PASSWORD=password-do-email
```

Guarda e sai: `Ctrl + O` → Enter → `Ctrl + X`

---

## Parte 4 — Abrir as portas no firewall

**Se usas UFW (Ubuntu):**

```bash
sudo ufw allow 22    # SSH (não feches isto!)
sudo ufw allow 80    # HTTP (necessário para o Let's Encrypt)
sudo ufw allow 443   # HTTPS
sudo ufw enable
sudo ufw status
```

**Se o servidor tem firewall externo** (painel do fornecedor de hosting):
Abre as portas TCP 80 e 443 no painel de controlo do servidor.

---

## Parte 5 — Iniciar a aplicação

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up --build -d
```

Este comando vai:
1. Descarregar e compilar tudo (5-10 minutos na primeira vez)
2. Obter automaticamente o certificado SSL do Let's Encrypt
3. Iniciar todos os serviços

Acompanha o progresso:

```bash
docker compose -f docker-compose.prod.yml logs -f
```

Quando vires `backend started` e `caddy started`, podes parar com `Ctrl + C`.

---

## Parte 6 — Verificar que está a funcionar

```bash
docker compose -f docker-compose.prod.yml ps
```

Deves ver 3 serviços com estado `running`:
```
NAME        STATUS
caddy       running
backend     running (healthy)
frontend    running
```

Abre o browser:
```
https://helpdesk.queiro.pt
```

Deves ver o ecrã de login com o cadeado verde (HTTPS activo).

---

## Parte 7 — Arranque automático após reiniciar o servidor

A configuração `restart: unless-stopped` já garante que os containers arrancam automaticamente. Para garantir que o Docker também arranca com o sistema:

```bash
sudo systemctl enable docker
```

---

## Comandos úteis do dia-a-dia

```bash
# Ver estado dos serviços
docker compose -f docker-compose.prod.yml ps

# Ver logs em tempo real
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f

# Ver apenas logs do backend
docker compose -f docker-compose.prod.yml logs backend

# Reiniciar tudo
docker compose -f docker-compose.prod.yml --env-file .env.prod restart

# Parar tudo
docker compose -f docker-compose.prod.yml --env-file .env.prod down

# Atualizar para nova versão
git pull
docker compose -f docker-compose.prod.yml --env-file .env.prod up --build -d
```

---

## Parte 8 — Migrar dados do Unraid para este servidor

Se já tinhas dados no Unraid e queres migrar tudo para aqui:

**No teu Mac** (ou qualquer computador com acesso a ambos os servidores):

```bash
# Copia a base de dados do Unraid para o servidor Linux
scp root@IP-DO-NAS:/mnt/cache/appdata/helpdesk/data/tickets.db \
    utilizador@helpdesk.queiro.pt:/opt/helpdesk/helpdesk_data/tickets.db
```

> **Nota:** O volume `helpdesk_data` fica em `/var/lib/docker/volumes/helpdesk_helpdesk_data/_data/` por defeito. Para simplificar, podes copiar directamente para lá:

```bash
# No servidor Linux:
docker compose -f docker-compose.prod.yml down

# No teu Mac:
scp root@IP-DO-NAS:/mnt/cache/appdata/helpdesk/data/tickets.db \
    utilizador@helpdesk.queiro.pt:/tmp/tickets.db

# No servidor Linux:
docker run --rm -v helpdesk_helpdesk_data:/data -v /tmp:/tmp alpine \
    cp /tmp/tickets.db /data/tickets.db

docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

Todos os tickets, utilizadores e categorias ficam migrados automaticamente.

---

## Resolução de problemas comuns

**Erro: "certificate authority error" ou SSL não funciona**

Verifica se o domínio aponta correctamente para o servidor:
```bash
dig helpdesk.queiro.pt +short
# Deve mostrar o IP do teu servidor
```
Se estiveres a usar Cloudflare, certifica-te que o proxy está em **DNS only** (nuvem cinzenta) durante a instalação inicial.

**Erro: "address already in use" (porta 80 ou 443 ocupada)**
```bash
sudo ss -tlnp | grep -E ':80|:443'
# Para ver que processo ocupa as portas
sudo systemctl stop nginx  # se for o nginx
sudo systemctl stop apache2  # se for o apache
```

**A aplicação não inicia depois de reboot**
```bash
sudo systemctl status docker
sudo systemctl start docker
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

**Ver erros detalhados**
```bash
docker compose -f docker-compose.prod.yml logs backend --tail=50
docker compose -f docker-compose.prod.yml logs caddy --tail=50
```

**Certificado SSL expirado** (raro — o Caddy renova automaticamente)
```bash
docker compose -f docker-compose.prod.yml restart caddy
```

---

## Backup automático recomendado

Adiciona esta linha ao crontab para backup diário da base de dados:

```bash
crontab -e
```

Adiciona:
```
0 3 * * * docker run --rm -v helpdesk_helpdesk_data:/data -v /opt/helpdesk/backups:/backup alpine cp /data/tickets.db /backup/tickets-$(date +\%Y\%m\%d).db
```

Isto cria um backup da base de dados todos os dias às 3h da manhã em `/opt/helpdesk/backups/`.

---

*Se precisares de ajuda, os logs do backend têm sempre a informação necessária para diagnosticar problemas: `docker compose -f docker-compose.prod.yml logs backend`*
