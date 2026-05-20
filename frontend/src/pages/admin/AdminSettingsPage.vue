<template>
  <div class="hd-page">
    <!-- Tabs -->
    <div class="hd-tabs" style="margin-bottom:24px">
      <button class="hd-tab" :class="{ active: tab === 'general' }" @click="tab = 'general'">
        <span class="material-icons" style="font-size:15px">tune</span> Geral
      </button>
      <button class="hd-tab" :class="{ active: tab === 'ldap' }" @click="tab = 'ldap'">
        <span class="material-icons" style="font-size:15px">dns</span> Active Directory
      </button>
      <button class="hd-tab" :class="{ active: tab === 'email' }" @click="tab = 'email'">
        <span class="material-icons" style="font-size:15px">email</span> Notificações
      </button>
      <button class="hd-tab" :class="{ active: tab === 'categories' }" @click="tab = 'categories'">
        <span class="material-icons" style="font-size:15px">category</span> Categorias e tempos de resposta
      </button>
      <button class="hd-tab" :class="{ active: tab === 'schools' }" @click="tab = 'schools'">
        <span class="material-icons" style="font-size:15px">account_balance</span> Escolas
      </button>
      <button class="hd-tab" :class="{ active: tab === 'routing' }" @click="tab = 'routing'">
        <span class="material-icons" style="font-size:15px">alt_route</span> Encaminhamento
      </button>
      <button class="hd-tab" :class="{ active: tab === 'knowledge' }" @click="tab = 'knowledge'">
        <span class="material-icons" style="font-size:15px">menu_book</span> Base de conhecimento
      </button>
    </div>

    <!-- General -->
    <div v-if="tab === 'general'" class="hd-card" style="padding:28px;max-width:640px">
      <div style="font-weight:600;font-size:15px;margin-bottom:20px">Configurações gerais</div>
      <div class="hd-field" style="margin-bottom:18px">
        <label class="hd-label">Nome do Agrupamento</label>
        <input class="hd-input" v-model="general.org_name" placeholder="Agrupamento de Escolas Eça de Queirós" />
      </div>
      <div class="hd-field" style="margin-bottom:18px">
        <label class="hd-label">Logotipo do Agrupamento</label>
        <input type="file" accept=".png,.jpg,.jpeg,.svg,.webp,image/png,image/jpeg,image/svg+xml,image/webp" @change="onLogoPicked" />
        <div v-if="general.logo_url" style="margin-top:10px">
          <img :src="general.logo_url" alt="Logotipo" style="max-width:180px;max-height:80px;object-fit:contain" />
        </div>
        <p class="hd-hint">PNG, JPG, SVG ou WEBP até 2 MB.</p>
      </div>
      <div class="hd-field" style="margin-bottom:18px">
        <label class="hd-label">URL base da aplicação</label>
        <input class="hd-input" v-model="general.app_url" placeholder="http://helpdesk.escola.local" />
      </div>
      <div class="hd-field" style="margin-bottom:18px">
        <label class="hd-label">Fuso horário</label>
        <select class="hd-select" v-model="general.timezone" style="max-width:300px">
          <option value="Europe/Lisbon">Europe/Lisbon</option>
          <option value="UTC">UTC</option>
        </select>
      </div>
      <div class="hd-field" style="margin-bottom:24px">
        <label class="hd-label">Duração da sessão (minutos)</label>
        <input class="hd-input" type="number" v-model="general.jwt_expire" style="max-width:140px" />
        <p class="hd-hint">Tempo até o token JWT expirar e o utilizador ter de iniciar sessão novamente.</p>
      </div>
      <div style="border-top:1px solid var(--c-border);padding-top:20px;margin-bottom:24px">
        <div style="font-weight:600;font-size:14px;margin-bottom:12px">Funcionalidades</div>
        <div class="hd-row" style="justify-content:space-between;align-items:center;padding:10px 0">
          <div>
            <div style="font-size:13px;font-weight:500">Avisos de categoria</div>
            <div style="font-size:12px;color:var(--c-muted)">Mostra uma janela de aviso ao selecionar categorias com aviso configurado</div>
          </div>
          <div class="hd-toggle-wrap" @click="toggleCategoryWarnings">
            <div class="hd-toggle" :class="{ active: categoryWarningsEnabled }"></div>
          </div>
        </div>
      </div>
      <div style="border-top:1px solid var(--c-border);padding-top:20px;margin-bottom:24px">
        <div style="font-weight:600;font-size:14px;margin-bottom:12px">Empresa de apoio informático</div>
        <div class="hd-grid-2">
          <div class="hd-field">
            <label class="hd-label">Nome da empresa</label>
            <input class="hd-input" v-model="general.support_provider_name" placeholder="Controlink" />
          </div>
          <div class="hd-field">
            <label class="hd-label">Email de suporte</label>
            <input class="hd-input" v-model="general.support_provider_email" placeholder="suporte@controlink.com" />
          </div>
        </div>
        <p class="hd-hint">Este email é usado quando um técnico/admin escala um ticket para a empresa de apoio.</p>
      </div>
      <button class="hd-btn hd-btn-primary" @click="saveGeneral">
        <span class="material-icons" style="font-size:16px">save</span> Guardar
      </button>
      <span v-if="saved" style="margin-left:12px;font-size:13px;color:#22C55E">Guardado!</span>
    </div>

    <!-- Schools -->
    <div v-if="tab === 'schools'" class="hd-card" style="padding:28px;max-width:760px">
      <div class="hd-row" style="margin-bottom:20px">
        <div style="font-weight:600;font-size:15px">Escolas</div>
        <div class="hd-spacer"></div>
        <button class="hd-btn hd-btn-primary" style="font-size:12px;padding:6px 14px" @click="showNewSchool = true">
          <span class="material-icons" style="font-size:14px">add</span> Nova escola
        </button>
      </div>
      <div v-if="loadingSchools" style="color:var(--c-muted)">A carregar...</div>
      <table v-else class="hd-table">
        <thead><tr><th>NOME</th><th>NOME CURTO</th><th>MORADA</th><th></th></tr></thead>
        <tbody>
          <tr v-for="school in schools" :key="school.id">
            <td style="font-weight:500">{{ school.name }}</td>
            <td style="font-size:12px;color:var(--c-muted)">{{ school.short_name }}</td>
            <td style="font-size:12px;color:var(--c-muted)">{{ school.address || '—' }}</td>
            <td>
              <button class="hd-icon-btn" @click="deleteSchool(school.id)" title="Eliminar">
                <span class="material-icons" style="font-size:15px;color:#EF4444">delete</span>
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="showNewSchool" style="margin-top:20px;border:1px solid var(--c-border);border-radius:10px;padding:20px">
        <div style="font-weight:600;font-size:14px;margin-bottom:16px">Nova escola</div>
        <div class="hd-grid-2" style="margin-bottom:12px">
          <div class="hd-field">
            <label class="hd-label">Nome</label>
            <input class="hd-input" v-model="newSchool.name" placeholder="Escola Eça de Queirós" />
          </div>
          <div class="hd-field">
            <label class="hd-label">Nome curto</label>
            <input class="hd-input" v-model="newSchool.short_name" placeholder="Eça" />
          </div>
        </div>
        <div class="hd-field" style="margin-bottom:16px">
          <label class="hd-label">Morada</label>
          <input class="hd-input" v-model="newSchool.address" placeholder="Morada da escola" />
        </div>
        <div class="hd-row" style="gap:8px;justify-content:flex-end">
          <button class="hd-btn hd-btn-outline" @click="showNewSchool = false">Cancelar</button>
          <button class="hd-btn hd-btn-primary" @click="createSchool" :disabled="!newSchool.name || !newSchool.short_name">
            Criar escola
          </button>
        </div>
      </div>
    </div>

    <!-- LDAP -->
    <div v-if="tab === 'ldap'" class="hd-card" style="padding:28px;max-width:640px">
      <div class="hd-row" style="margin-bottom:20px">
        <div style="font-weight:600;font-size:15px">Configuração LDAP / Active Directory</div>
        <div class="hd-spacer"></div>
        <label class="hd-row" style="gap:8px;cursor:pointer;font-size:13px">
          <div class="hd-toggle-wrap" @click="ldap.enabled = !ldap.enabled">
            <div class="hd-toggle" :class="{ active: ldap.enabled }"></div>
          </div>
          {{ ldap.enabled ? 'Ativo' : 'Inativo' }}
        </label>
      </div>

      <div :style="{ opacity: ldap.enabled ? 1 : 0.5, pointerEvents: ldap.enabled ? 'auto' : 'none' }">
        <div class="hd-field" style="margin-bottom:16px">
          <label class="hd-label">Servidor LDAP</label>
          <input class="hd-input" v-model="ldap.server" placeholder="ldaps://dc.escola.local" />
        </div>
        <div class="hd-grid-2" style="margin-bottom:16px">
          <div class="hd-field">
            <label class="hd-label">Porta</label>
            <input class="hd-input" type="number" v-model="ldap.port" placeholder="636" />
          </div>
          <div class="hd-field">
            <label class="hd-label">Protocolo</label>
            <select class="hd-select" v-model="ldap.tls">
              <option value="ldaps">LDAPS (recomendado)</option>
              <option value="ldap">LDAP + STARTTLS</option>
              <option value="plain">LDAP simples</option>
            </select>
          </div>
        </div>
        <div class="hd-field" style="margin-bottom:16px">
          <label class="hd-label">Bind DN (conta de serviço)</label>
          <input class="hd-input" v-model="ldap.bind_dn" placeholder="cn=svc_tickets,ou=ServiceAccounts,dc=escola,dc=local" />
        </div>
        <div class="hd-field" style="margin-bottom:16px">
          <label class="hd-label">Palavra-passe</label>
          <input class="hd-input" type="password" v-model="ldap.bind_password" placeholder="••••••••" />
        </div>
        <div class="hd-field" style="margin-bottom:16px">
          <label class="hd-label">Base DN</label>
          <input class="hd-input" v-model="ldap.base_dn" placeholder="ou=Staff,dc=escola,dc=local" />
        </div>
        <div class="hd-field" style="margin-bottom:24px">
          <label class="hd-label">Grupo de administradores (DN)</label>
          <input class="hd-input" v-model="ldap.admin_group" placeholder="CN=TI-Suporte,ou=Groups,dc=escola,dc=local" />
          <p class="hd-hint">Membros deste grupo recebem automaticamente o papel de Administrador.</p>
        </div>
        <div class="hd-row" style="gap:10px">
          <button class="hd-btn hd-btn-outline" @click="testLdap" :disabled="testing">
            <span class="material-icons" style="font-size:16px">cable</span>
            {{ testing ? 'A testar...' : 'Testar ligação' }}
          </button>
          <span v-if="ldapTestResult" :style="{ color: ldapTestOk ? '#22C55E' : '#EF4444', fontSize: '13px' }">
            {{ ldapTestResult }}
          </span>
          <div class="hd-spacer"></div>
          <button class="hd-btn hd-btn-primary" @click="saved = true">
            <span class="material-icons" style="font-size:16px">save</span> Guardar
          </button>
        </div>
      </div>
    </div>

    <!-- Email / notifications -->
    <div v-if="tab === 'email'" class="hd-card" style="padding:28px;max-width:640px">
      <div style="font-weight:600;font-size:15px;margin-bottom:20px">Configuração de email</div>
      <div class="hd-grid-2" style="margin-bottom:16px">
        <div class="hd-field">
          <label class="hd-label">Servidor SMTP</label>
          <input class="hd-input" v-model="email.server" placeholder="smtp.escola.local" />
        </div>
        <div class="hd-field">
          <label class="hd-label">Porta</label>
          <input class="hd-input" type="number" v-model="email.port" placeholder="587" />
        </div>
      </div>
      <div class="hd-field" style="margin-bottom:16px">
        <label class="hd-label">Endereço remetente</label>
        <input class="hd-input" v-model="email.from" placeholder="tickets@escola.local" />
      </div>
      <div class="hd-field" style="margin-bottom:16px">
        <label class="hd-label">Utilizador SMTP</label>
        <input class="hd-input" v-model="email.username" />
      </div>
      <div class="hd-field" style="margin-bottom:24px">
        <label class="hd-label">Palavra-passe SMTP</label>
        <input class="hd-input" type="password" v-model="email.password" placeholder="••••••••" />
      </div>

      <div style="border-top:1px solid var(--c-border);padding-top:20px;margin-bottom:20px">
        <div style="font-weight:600;font-size:14px;margin-bottom:12px">Notificações automáticas</div>
        <div style="display:flex;flex-direction:column;gap:12px">
          <div v-for="n in notifications" :key="n.key" class="hd-row" style="justify-content:space-between">
            <div>
              <div style="font-size:13px;font-weight:500">{{ n.label }}</div>
              <div style="font-size:12px;color:var(--c-muted)">{{ n.desc }}</div>
            </div>
            <div class="hd-toggle-wrap" @click="n.enabled = !n.enabled">
              <div class="hd-toggle" :class="{ active: n.enabled }"></div>
            </div>
          </div>
        </div>
      </div>
      <div style="border-top:1px solid var(--c-border);padding-top:20px;margin-top:4px">
        <div style="font-weight:600;font-size:14px;margin-bottom:10px">Teste de email</div>
        <p class="hd-hint" style="margin-bottom:12px">Envia um email de teste para o endereço do utilizador atual, para verificar se as notificações estão a funcionar.</p>
        <div class="hd-row" style="gap:10px;align-items:center">
          <button class="hd-btn hd-btn-outline" :disabled="testingSmtp" @click="testSmtpNow">
            <span class="material-icons" style="font-size:16px">send</span>
            {{ testingSmtp ? 'A enviar...' : 'Enviar email de teste' }}
          </button>
          <span v-if="smtpTestResult" :style="{ color: smtpTestOk ? '#22C55E' : '#EF4444', fontSize: '13px' }">
            {{ smtpTestResult }}
          </span>
        </div>
      </div>
      <div style="border-top:1px solid var(--c-border);padding-top:20px;margin-top:4px">
        <div style="font-weight:600;font-size:14px;margin-bottom:10px">Teste de notificação push</div>
        <p class="hd-hint" style="margin-bottom:12px">
          Envia uma notificação push de teste para este dispositivo.
          Clique primeiro na campainha (canto superior direito) → <strong>Ativar</strong> para registar este browser.
        </p>
        <div style="display:flex;flex-direction:column;gap:8px">
          <div class="hd-row" style="gap:10px;align-items:center">
            <button class="hd-btn hd-btn-outline" :disabled="testingPush" @click="testPushNow">
              <span class="material-icons" style="font-size:16px">notifications_active</span>
              {{ testingPush ? 'A enviar...' : 'Enviar notificação de teste' }}
            </button>
            <span v-if="pushTestResult && pushTestOk" style="color:#22C55E;font-size:13px">{{ pushTestResult }}</span>
          </div>
          <div v-if="pushTestResult && !pushTestOk" style="background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.3);border-radius:8px;padding:12px 14px">
            <div style="font-size:13px;color:#EF4444;font-weight:600;margin-bottom:4px">{{ pushTestResult }}</div>
            <div style="font-size:12px;color:var(--c-muted);line-height:1.5">
              Clique na <strong>campainha</strong> no topo da página → <strong>Ativar</strong> para registar este dispositivo.<br>
              Se já ativou antes e continua a falhar, clique em <strong>Desativar</strong> e depois <strong>Ativar</strong> novamente para re-sincronizar.
            </div>
          </div>
        </div>
      </div>
      <div style="border-top:1px solid var(--c-border);padding-top:20px;margin-top:4px">
        <div style="font-weight:600;font-size:14px;margin-bottom:6px">Destinatários das sugestões</div>
        <p class="hd-hint" style="margin-bottom:12px">
          Quando um utilizador envia uma sugestão, é enviado um email de notificação para os endereços abaixo.
          Separe vários endereços com vírgula.
        </p>
        <input
          class="hd-input"
          v-model="suggestionEmailsRaw"
          placeholder="admin@escola.pt, diretor@escola.pt"
        />
      </div>
      <div style="margin-top:20px">
        <button class="hd-btn hd-btn-primary" @click="saveEmailSettings">
          <span class="material-icons" style="font-size:16px">save</span> Guardar
        </button>
        <span v-if="savedEmail" style="margin-left:12px;font-size:13px;color:#22C55E">Guardado!</span>
      </div>
    </div>

    <!-- Categories -->
    <div v-if="tab === 'categories'" class="hd-card" style="padding:28px;max-width:980px">
      <div class="hd-row" style="margin-bottom:20px">
        <div style="font-weight:600;font-size:15px">Categorias e tempos de resposta</div>
        <div class="hd-spacer"></div>
        <button class="hd-btn hd-btn-primary" style="font-size:12px;padding:6px 14px" @click="showNewCat = true">
          <span class="material-icons" style="font-size:14px">add</span> Nova categoria
        </button>
      </div>
      <div v-if="loadingCats" style="color:var(--c-muted)">A carregar...</div>
      <table v-else class="hd-table">
        <thead><tr><th>ÍCONE</th><th>NOME</th><th>DESCRIÇÃO</th><th>EMAIL</th><th>TEMPO DE RESPOSTA</th><th></th></tr></thead>
        <tbody>
          <tr v-for="cat in categories" :key="cat.id">
            <td>
              <div style="width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center"
                :style="{ background: cat.color + '22' }">
                <span class="material-icons" :style="{ color: cat.color, fontSize: '16px' }">{{ cat.icon }}</span>
              </div>
            </td>
            <td style="font-weight:500">{{ cat.name }}</td>
            <td style="font-size:12px;color:var(--c-muted)">{{ cat.description }}</td>
            <td style="min-width:220px">
              <input
                class="hd-input"
                style="padding:5px 8px;font-size:12px"
                v-model="cat.email_to"
                placeholder="email@escola.pt"
                @change="saveCategoryEmail(cat)"
              />
            </td>
            <td style="font-weight:600">{{ cat.sla_hours }}h</td>
            <td>
              <button class="hd-icon-btn" @click="deleteCategory(cat.id)" title="Eliminar">
                <span class="material-icons" style="font-size:15px;color:#EF4444">delete</span>
              </button>
            </td>
          </tr>
          <tr v-if="!categories.length">
            <td colspan="6" style="text-align:center;color:var(--c-muted);padding:32px">Sem categorias.</td>
          </tr>
        </tbody>
      </table>

      <!-- New category form -->
      <div v-if="showNewCat" style="margin-top:20px;border:1px solid var(--c-border);border-radius:10px;padding:20px">
        <div style="font-weight:600;font-size:14px;margin-bottom:16px">Nova categoria</div>
        <div class="hd-grid-2" style="margin-bottom:12px">
          <div class="hd-field">
            <label class="hd-label">Nome</label>
            <input class="hd-input" v-model="newCat.name" placeholder="Ex: Equipamento TI" />
          </div>
          <div class="hd-field">
            <label class="hd-label">Tempo de resposta (horas)</label>
            <input class="hd-input" type="number" v-model="newCat.sla_hours" placeholder="48" />
          </div>
        </div>
        <div class="hd-field" style="margin-bottom:12px">
          <label class="hd-label">Descrição</label>
          <input class="hd-input" v-model="newCat.description" placeholder="Breve descrição da categoria" />
        </div>
        <div class="hd-field" style="margin-bottom:12px">
          <label class="hd-label">Email de notificação</label>
          <input class="hd-input" v-model="newCat.email_to" placeholder="ex: inovar@escola.pt" />
        </div>
        <div class="hd-grid-2" style="margin-bottom:16px">
          <div class="hd-field">
            <label class="hd-label">Ícone Material Icons</label>
            <input class="hd-input" v-model="newCat.icon" placeholder="computer" />
          </div>
          <div class="hd-field">
            <label class="hd-label">Cor (hex)</label>
            <div class="hd-row" style="gap:8px">
              <input class="hd-input" v-model="newCat.color" placeholder="#3D52D5" style="flex:1" />
              <input type="color" v-model="newCat.color" style="width:40px;height:36px;border:none;background:none;cursor:pointer" />
            </div>
          </div>
        </div>
        <div class="hd-row" style="gap:8px;justify-content:flex-end">
          <button class="hd-btn hd-btn-outline" @click="showNewCat = false">Cancelar</button>
          <button class="hd-btn hd-btn-primary" @click="createCat" :disabled="!newCat.name">
            Criar categoria
          </button>
        </div>
      </div>
    </div>

    <div v-if="tab === 'routing'" class="hd-card" style="padding:28px;max-width:1100px">
      <div style="font-weight:600;font-size:15px;margin-bottom:4px">Encaminhamento automático</div>
      <p class="hd-hint" style="margin-bottom:18px">Quando um ticket é criado, a primeira regra compatível atribui automaticamente grupo e/ou responsável.</p>
      <div class="routing-form">
        <select class="hd-select" v-model="newRoute.category_id">
          <option :value="''">Qualquer categoria</option>
          <option v-for="c in categories" :key="c.id" :value="String(c.id)">{{ c.name }}</option>
        </select>
        <select class="hd-select" v-model="newRoute.school_id">
          <option :value="''">Qualquer escola</option>
          <option v-for="s in schools" :key="s.id" :value="String(s.id)">{{ s.name }}</option>
        </select>
        <select class="hd-select" v-model="newRoute.group_id">
          <option :value="''">Sem grupo</option>
          <option v-for="g in groups" :key="g.id" :value="String(g.id)">{{ g.name }}</option>
        </select>
        <select class="hd-select" v-model="newRoute.assignee_id">
          <option :value="''">Sem responsável</option>
          <option v-for="u in staffUsers" :key="u.id" :value="String(u.id)">{{ u.display_name }}</option>
        </select>
        <input class="hd-input" type="number" v-model="newRoute.priority" title="Prioridade" />
        <button class="hd-btn hd-btn-primary" @click="addRoute">Adicionar regra</button>
      </div>
      <table class="hd-table">
        <thead><tr><th>Categoria</th><th>Escola</th><th>Grupo</th><th>Responsável</th><th>Ordem</th><th></th></tr></thead>
        <tbody>
          <tr v-for="rule in routingRules" :key="rule.id">
            <td>{{ rule.category?.name || 'Qualquer' }}</td>
            <td>{{ rule.school?.name || 'Qualquer' }}</td>
            <td>{{ rule.group?.name || '—' }}</td>
            <td>{{ rule.assignee?.display_name || '—' }}</td>
            <td>{{ rule.priority }}</td>
            <td>
              <button class="hd-icon-btn" @click="removeRoute(rule.id)" title="Eliminar">
                <span class="material-icons" style="font-size:15px;color:#EF4444">delete</span>
              </button>
            </td>
          </tr>
          <tr v-if="!routingRules.length">
            <td colspan="6" style="text-align:center;color:var(--c-muted);padding:32px">Sem regras de encaminhamento.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="tab === 'knowledge'" class="hd-card" style="padding:28px;max-width:1100px">
      <div class="hd-row" style="align-items:flex-start;gap:16px;margin-bottom:18px">
        <div>
          <div style="font-weight:600;font-size:15px;margin-bottom:4px">Base de conhecimento</div>
          <p class="hd-hint">Artigos visíveis aos utilizadores para respostas rápidas e redução de tickets repetidos.</p>
        </div>
        <div class="hd-spacer"></div>
        <button class="hd-btn" :class="knowledgeEnabled ? 'hd-btn-primary' : 'hd-btn-outline'" @click="toggleKnowledge">
          <span class="material-icons" style="font-size:16px">{{ knowledgeEnabled ? 'visibility' : 'visibility_off' }}</span>
          {{ knowledgeEnabled ? 'Base ativa' : 'Base escondida' }}
        </button>
      </div>

      <div v-if="!knowledgeEnabled" class="feature-disabled-note">
        A Base de conhecimento está escondida no menu dos utilizadores e a página pública está bloqueada.
      </div>

      <div class="knowledge-form">
        <input class="hd-input" v-model="newArticle.title" placeholder="Título do artigo" />
        <select class="hd-select" v-model="newArticle.category_id">
          <option :value="''">Sem categoria</option>
          <option v-for="c in categories" :key="c.id" :value="String(c.id)">{{ c.name }}</option>
        </select>
        <label class="publish-toggle">
          <input type="checkbox" v-model="newArticle.is_published" />
          Publicado
        </label>
        <textarea class="hd-textarea" v-model="newArticle.body" rows="4" placeholder="Conteúdo do artigo"></textarea>
        <button class="hd-btn hd-btn-primary" @click="addArticle" :disabled="!newArticle.title || !newArticle.body">Adicionar artigo</button>
      </div>

      <table class="hd-table">
        <thead><tr><th>TÍTULO</th><th>CATEGORIA</th><th>ESTADO</th><th></th></tr></thead>
        <tbody>
          <tr v-for="article in articles" :key="article.id">
            <td style="font-weight:700">{{ article.title }}</td>
            <td>{{ article.category?.name || '—' }}</td>
            <td>{{ article.is_published ? 'Publicado' : 'Rascunho' }}</td>
            <td>
              <button class="hd-icon-btn" @click="removeArticle(article.id)" title="Eliminar">
                <span class="material-icons" style="font-size:15px;color:#EF4444">delete</span>
              </button>
            </td>
          </tr>
          <tr v-if="!articles.length">
            <td colspan="4" style="text-align:center;color:var(--c-muted);padding:32px">Sem artigos.</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { createCategory, createKnowledgeArticle, createRoutingRule, createSchool as apiCreateSchool, deleteCategory as apiDeleteCategory, deleteKnowledgeArticle, deleteRoutingRule, deleteSchool as apiDeleteSchool, getCategories, getKnowledgeArticles, getRoutingRules, getSchools, updateCategory as apiUpdateCategory, testSmtp, testPush as apiTestPush } from '../../api/tickets'
import { getPublicSettings, updateFeatureSettings, updateSettings } from '../../api/settings'
import { api } from '../../boot/axios'
import { getGroups, getUsers } from '../../api/users'

const tab = ref<'general' | 'ldap' | 'email' | 'categories' | 'schools' | 'routing' | 'knowledge'>('general')
const saved = ref(false)
const testing = ref(false)
const ldapTestResult = ref('')
const ldapTestOk = ref(false)
const testingSmtp = ref(false)
const smtpTestResult = ref('')
const smtpTestOk = ref(false)
const testingPush = ref(false)
const pushTestResult = ref('')
const pushTestOk = ref(false)
const showNewCat = ref(false)
const showNewSchool = ref(false)
const loadingCats = ref(false)
const loadingSchools = ref(false)
const categories = ref<any[]>([])
const schools = ref<any[]>([])
const groups = ref<any[]>([])
const staffUsers = ref<any[]>([])
const routingRules = ref<any[]>([])
const articles = ref<any[]>([])
const logoFile = ref<File | null>(null)
const knowledgeEnabled = ref(true)
const categoryWarningsEnabled = ref(true)

const general = ref({ org_name: '', logo_url: '', app_url: '', timezone: 'Europe/Lisbon', jwt_expire: 480, support_provider_name: 'Empresa de apoio informático', support_provider_email: '' })
const ldap = ref({ enabled: true, server: '', port: 636, tls: 'ldaps', bind_dn: '', bind_password: '', base_dn: '', admin_group: '' })
const email = ref({ server: '', port: 587, from: '', username: '', password: '' })
const suggestionEmailsRaw = ref('')
const savedEmail = ref(false)

const notifications = ref([
  { key: 'ticket_created', label: 'Ticket criado', desc: 'Notifica o solicitante quando o ticket é aberto', enabled: true },
  { key: 'ticket_assigned', label: 'Ticket atribuído', desc: 'Notifica o técnico quando lhe é atribuído um ticket', enabled: true },
  { key: 'ticket_updated', label: 'Ticket atualizado', desc: 'Notifica quando o estado muda', enabled: true },
  { key: 'ticket_resolved', label: 'Ticket resolvido', desc: 'Notifica o solicitante quando o ticket é resolvido', enabled: true },
])

const newCat = ref({ name: '', description: '', email_to: '', icon: 'help', color: '#3D52D5', sla_hours: 48 })
const newSchool = ref({ name: '', short_name: '', address: '' })
const newRoute = ref({ category_id: '', school_id: '', group_id: '', assignee_id: '', priority: 100 })
const newArticle = ref({ title: '', body: '', category_id: '', is_published: true })

onMounted(async () => {
  loadingCats.value = true
  loadingSchools.value = true
  try {
    const [settings, cats, schs, grps, users, routes, kb] = await Promise.all([getPublicSettings(), getCategories(), getSchools(), getGroups(), getUsers(), getRoutingRules(), getKnowledgeArticles(true)])
    general.value.org_name = settings.org_name
    general.value.logo_url = settings.logo_url
    general.value.support_provider_name = settings.support_provider_name || 'Empresa de apoio informático'
    general.value.support_provider_email = settings.support_provider_email || ''
    knowledgeEnabled.value = settings.knowledge_enabled !== false
    categoryWarningsEnabled.value = settings.category_warnings_enabled !== false
    suggestionEmailsRaw.value = (settings.suggestion_emails || []).join(', ')
    categories.value = cats
    schools.value = schs
    groups.value = grps
    staffUsers.value = users.filter((u: any) => u.is_active && (u.role === 'technician' || u.is_technician))
    routingRules.value = routes
    articles.value = kb
  } finally {
    loadingCats.value = false
    loadingSchools.value = false
  }
})

function onLogoPicked(event: Event) {
  const input = event.target as HTMLInputElement
  logoFile.value = input.files?.[0] ?? null
}

async function saveGeneral() {
  try {
    const settings = await updateSettings({
      org_name: general.value.org_name,
      support_provider_name: general.value.support_provider_name,
      support_provider_email: general.value.support_provider_email,
      logo: logoFile.value,
    })
    general.value.org_name = settings.org_name
    general.value.logo_url = settings.logo_url
    general.value.support_provider_name = settings.support_provider_name || 'Empresa de apoio informático'
    general.value.support_provider_email = settings.support_provider_email || ''
    logoFile.value = null
    saved.value = true
  } catch { /* ignore */ }
}

async function toggleKnowledge() {
  const next = !knowledgeEnabled.value
  const saved = await updateFeatureSettings({ knowledge_enabled: next, category_warnings_enabled: categoryWarningsEnabled.value })
  knowledgeEnabled.value = saved.knowledge_enabled
}

async function toggleCategoryWarnings() {
  const next = !categoryWarningsEnabled.value
  const saved = await updateFeatureSettings({ knowledge_enabled: knowledgeEnabled.value, category_warnings_enabled: next })
  categoryWarningsEnabled.value = saved.category_warnings_enabled
}

async function testSmtpNow() {
  testingSmtp.value = true
  smtpTestResult.value = ''
  try {
    const r = await testSmtp()
    smtpTestOk.value = true
    smtpTestResult.value = `Email enviado para ${r.sent_to}`
  } catch (e: any) {
    smtpTestOk.value = false
    smtpTestResult.value = e?.response?.data?.detail || 'Erro ao enviar email de teste'
  } finally {
    testingSmtp.value = false
  }
}

async function testPushNow() {
  testingPush.value = true
  pushTestResult.value = ''
  try {
    await apiTestPush()
    pushTestOk.value = true
    pushTestResult.value = 'Notificação enviada!'
  } catch (e: any) {
    pushTestOk.value = false
    pushTestResult.value = e?.response?.data?.detail || 'Erro ao enviar notificação push'
  } finally {
    testingPush.value = false
  }
}

async function saveEmailSettings() {
  savedEmail.value = false
  const emails = suggestionEmailsRaw.value
    .split(',')
    .map((e: string) => e.trim())
    .filter((e: string) => e.includes('@'))
  try {
    await api.put('/api/v1/settings/suggestion-emails', { emails })
    savedEmail.value = true
    setTimeout(() => { savedEmail.value = false }, 3000)
  } catch { /* ignore */ }
}

async function testLdap() {
  testing.value = true
  ldapTestResult.value = ''
  await new Promise(r => setTimeout(r, 1200))
  ldapTestOk.value = false
  ldapTestResult.value = 'Configure o servidor no .env e reinicie o backend para testar.'
  testing.value = false
}

async function createCat() {
  try {
    const cat = await createCategory({ ...newCat.value })
    categories.value.push(cat)
    showNewCat.value = false
    newCat.value = { name: '', description: '', email_to: '', icon: 'help', color: '#3D52D5', sla_hours: 48 }
  } catch { /* ignore */ }
}

async function saveCategoryEmail(cat: any) {
  try {
    const updated = await apiUpdateCategory(cat.id, { email_to: cat.email_to || '' })
    const idx = categories.value.findIndex(c => c.id === cat.id)
    if (idx !== -1) categories.value[idx] = { ...categories.value[idx], ...updated }
  } catch { /* ignore */ }
}

async function deleteCategory(id: number) {
  if (!confirm('Eliminar esta categoria?')) return
  try {
    await apiDeleteCategory(id)
    categories.value = categories.value.filter(c => c.id !== id)
  } catch { /* ignore */ }
}

async function createSchool() {
  try {
    const school = await apiCreateSchool({ ...newSchool.value })
    schools.value.push(school)
    showNewSchool.value = false
    newSchool.value = { name: '', short_name: '', address: '' }
  } catch { /* ignore */ }
}

async function deleteSchool(id: number) {
  if (!confirm('Eliminar esta escola?')) return
  try {
    await apiDeleteSchool(id)
    schools.value = schools.value.filter(s => s.id !== id)
  } catch { /* ignore */ }
}

async function addRoute() {
  const route = await createRoutingRule({
    category_id: newRoute.value.category_id ? Number(newRoute.value.category_id) : null,
    school_id: newRoute.value.school_id ? Number(newRoute.value.school_id) : null,
    group_id: newRoute.value.group_id ? Number(newRoute.value.group_id) : null,
    assignee_id: newRoute.value.assignee_id ? Number(newRoute.value.assignee_id) : null,
    priority: Number(newRoute.value.priority) || 100,
  })
  routingRules.value.push(route)
  routingRules.value.sort((a, b) => a.priority - b.priority)
  newRoute.value = { category_id: '', school_id: '', group_id: '', assignee_id: '', priority: 100 }
}

async function removeRoute(id: number) {
  if (!confirm('Eliminar esta regra?')) return
  await deleteRoutingRule(id)
  routingRules.value = routingRules.value.filter(r => r.id !== id)
}

async function addArticle() {
  const article = await createKnowledgeArticle({
    title: newArticle.value.title,
    body: newArticle.value.body,
    category_id: newArticle.value.category_id ? Number(newArticle.value.category_id) : null,
    is_published: newArticle.value.is_published,
  })
  articles.value.unshift(article)
  newArticle.value = { title: '', body: '', category_id: '', is_published: true }
}

async function removeArticle(id: number) {
  if (!confirm('Eliminar este artigo?')) return
  await deleteKnowledgeArticle(id)
  articles.value = articles.value.filter(a => a.id !== id)
}

</script>

<style scoped>
.routing-form {
  display: grid;
  grid-template-columns: repeat(4, minmax(150px, 1fr)) 90px auto;
  gap: 10px;
  margin-bottom: 18px;
}
.knowledge-form {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) 220px auto;
  gap: 10px;
  margin-bottom: 20px;
}
.knowledge-form .hd-textarea {
  grid-column: 1 / -1;
}
.publish-toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--c-muted);
  font-weight: 700;
}
.feature-disabled-note {
  background: rgba(245, 158, 11, .1);
  border: 1px solid rgba(245, 158, 11, .28);
  border-radius: 10px;
  color: #92400E;
  font-size: 13px;
  line-height: 1.45;
  margin-bottom: 18px;
  padding: 12px 14px;
}
.dark .feature-disabled-note {
  color: #FCD34D;
}
@media (max-width: 900px) {
  .routing-form { grid-template-columns: 1fr; }
  .knowledge-form { grid-template-columns: 1fr; }
}
</style>
