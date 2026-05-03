# Guia de Instalação — Unraid NAS

> **Para quem é este guia?** Para alguém que nunca instalou Docker ou aplicações via linha de comandos no Unraid. Segue os passos pela ordem indicada e terás o sistema a funcionar.

---

## O que vais precisar

- Unraid com acesso à interface web (normalmente `http://torre` ou `http://IP-DO-NAS`)
- Acesso ao terminal do Unraid (via SSH ou diretamente pelo browser)
- Ligação à Internet (para descarregar as imagens Docker)
- 10 minutos

---

## Parte 1 — Preparar a pasta de dados

Abre o terminal do Unraid. Podes fazer isso de duas formas:

**Opção A — pelo browser:**
Na interface do Unraid → menu superior → **Tools** → **Terminal**

**Opção B — via SSH do teu Mac:**
```bash
ssh root@IP-DO-NAS
```

No terminal, cria a pasta onde a aplicação vai guardar os dados:

```bash
mkdir -p /mnt/cache/appdata/helpdesk
```

> **Porquê `/mnt/cache`?** É o disco cache do Unraid — mais rápido para aplicações. Os dados ficam sempre aí mesmo que reinicies.

---

## Parte 2 — Copiar os ficheiros da aplicação

Ainda no terminal do Unraid, descarrega o código do GitHub:

```bash
cd /mnt/cache/appdata/helpdesk
git clone https://github.com/sendas/helpdesk-escolar.git .
```

> O ponto (`.`) no final é importante — diz ao git para copiar os ficheiros directamente para esta pasta, sem criar uma subpasta.

Verifica que funcionou:

```bash
ls
```

Deves ver: `backend  frontend  docker-compose.yml  docker-compose.unraid.yml  app.env.unraid.example  README.md`

---

## Parte 3 — Criar o ficheiro de configuração

O ficheiro `app.env` contém as definições da aplicação (como palavras-passe e endereços de servidor). No Unraid usamos `app.env` em vez de `.env` para evitar problemas com passwords que tenham `$`.

```bash
cp app.env.unraid.example app.env
```

Agora edita o ficheiro:

```bash
nano app.env
```

O nano é um editor de texto simples. Usa as setas do teclado para navegar.

**Muda estas linhas obrigatoriamente:**

```
APP_SECRET_KEY=muda-isto-para-uma-frase-aleatoria-longa
FRONTEND_URL=https://sendas.tplinkdns.com
LDAP_ENABLED=false
AZURE_AD_ENABLED=true
MAIL_SUPPRESS_SEND=true
```

> Substitui `sendas.tplinkdns.com` pelo dominio HTTPS que aponta para o teu NAS/reverse proxy.
> Para login Microsoft, o Microsoft Entra ID exige HTTPS. URLs `http://192.168...` nao sao aceites como redirect URI.

**Para a autenticação (escolhe uma opção):**

Se ainda não tens Active Directory configurado, deixa o modo demo ativo (já está por defeito) — consegues entrar com utilizadores demo para testar.

Se tens LDAP no teu servidor de escola:
```
LDAP_ENABLED=true
LDAP_SERVER=ldaps://10.114.80.4
LDAP_PORT=636
LDAP_BIND_DN=cn=svc_tickets,ou=ServiceAccounts,dc=escola,dc=local
LDAP_BIND_PASSWORD=password-da-conta-de-servico
LDAP_BASE_DN=ou=Staff,dc=escola,dc=local
LDAP_ADMIN_GROUP=CN=TI-Suporte,ou=Groups,dc=escola,dc=local
```

Se o container nao conseguir resolver o nome do servidor, usa o IP do controlador de dominio:
```
LDAP_SERVER=ldaps://10.114.80.4
```

Como o Unraid usa `app.env`, podes escrever passwords com `$` normalmente nesse ficheiro. Se ainda tiveres uma configuracao antiga em `.env`, muda-a para `app.env` e remove o `.env` para o Docker Compose deixar de tentar interpretar esses valores.

Se tambem quiseres login por Azure AD / Entra ID, ativa-o apenas depois de criares a aplicacao no portal Microsoft:
```
AZURE_AD_ENABLED=true
AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_SECRET=segredo-da-aplicacao
AZURE_REDIRECT_URI=https://sendas.tplinkdns.com/api/v1/auth/azure-callback
```

**Para guardar e sair do nano:**
- `Ctrl + O` → Enter (guarda)
- `Ctrl + X` (sai)

---

## Parte 4 — Iniciar a aplicação

```bash
docker compose -f docker-compose.unraid.yml up --build -d
```

Este comando vai:
1. Descarregar as imagens necessárias (pode demorar 2-5 minutos na primeira vez)
2. Compilar o frontend
3. Iniciar os serviços em segundo plano

Quando terminar, verifica se está a correr:

```bash
docker compose -f docker-compose.unraid.yml ps
```

Deves ver algo como:
```
NAME         STATUS
backend      running (healthy)
frontend     running
```

---

## Parte 5 — Aceder à aplicação

Abre o browser e vai a:

```
http://IP-DO-NAS:85
```

Por exemplo: `http://192.168.1.50:85`

Deves ver o ecrã de login. Clica em **"Entrar em modo demo"** para testar sem precisar de configurar o Active Directory.

---

## Parte 6 — Criar categorias iniciais (primeiro login)

Entra com o perfil **Administrador** (modo demo). Depois vai a:

**Configurações → Categorias e SLAs → Nova categoria**

Exemplos de categorias para uma escola:
| Nome | Ícone | SLA |
|------|-------|-----|
| Equipamento TI | `computer` | 24h |
| Rede e Internet | `wifi` | 8h |
| Software e Licenças | `apps` | 48h |
| Projetores e AV | `videocam` | 4h |
| Impressoras | `print` | 24h |
| Infraestrutura | `build` | 72h |
| Pedagógico | `school` | 48h |

---

## Parte 7 — Reiniciar automaticamente com o Unraid

A configuração `restart: unless-stopped` nos ficheiros docker-compose já garante que os containers arrancam automaticamente quando o Unraid reinicia. Não precisas de fazer nada adicional.

---

## Comandos úteis do dia-a-dia

```bash
# Ver os logs (útil se algo não funcionar)
docker compose -f docker-compose.unraid.yml logs -f

# Parar a aplicação
docker compose -f docker-compose.unraid.yml down

# Reiniciar a aplicação
docker compose -f docker-compose.unraid.yml restart

# Atualizar para nova versão (depois de um git pull)
git pull
docker compose -f docker-compose.unraid.yml up --build -d
```

---

## Resolução de problemas comuns

**Erro: "port is already allocated"**
Já há outro serviço a usar a porta 85 ou 8089. Edita o `docker-compose.unraid.yml` e muda a porta. Por exemplo: `"8085:80"` em vez de `"85:80"`.

**Erro: "permission denied"**
```bash
chmod -R 755 /mnt/cache/appdata/helpdesk
```

**A página aparece mas o login não funciona**
Verifica o `FRONTEND_URL` no `app.env` — tem de corresponder exactamente ao endereço que usas no browser (com o IP correcto).

**Aviso: The "xxx" variable is not set**
Existe um `.env` antigo na pasta e alguma password tem `$`. Migra para `app.env`:
```bash
mv .env app.env
docker compose -f docker-compose.unraid.yml down
docker compose -f docker-compose.unraid.yml up -d
```

**Ver erros detalhados do backend**
```bash
docker logs $(docker ps -qf name=backend)
```

---

## Onde ficam os dados

Todos os dados (tickets, utilizadores, categorias) ficam num único ficheiro:

```
/mnt/cache/appdata/helpdesk/data/tickets.db
```

Para fazer backup manual, basta copiar este ficheiro.

---

*Próximo passo: se quiseres migrar para o servidor Linux com HTTPS, consulta o **GUIA-LINUX.md**.*
