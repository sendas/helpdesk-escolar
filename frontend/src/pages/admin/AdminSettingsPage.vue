<template>
  <div class="hd-page settings-page">
    <!-- Section navigation -->
    <nav class="set-nav" aria-label="Secções das configurações">
      <template v-for="g in navGroups" :key="g.label">
        <div class="set-nav-group">{{ g.label }}</div>
        <button
          v-for="it in g.items"
          :key="it.key"
          class="set-nav-item"
          :class="{ active: section === it.key }"
          @click="go(it.key)"
        >
          <span class="material-icons">{{ it.icon }}</span>
          <span>{{ it.label }}</span>
          <span v-if="it.badge" class="set-nav-badge" :class="it.badge.cls">{{ it.badge.text }}</span>
        </button>
      </template>
    </nav>
    <select class="hd-select set-nav-mobile" :value="section" @change="go(($event.target as HTMLSelectElement).value)">
      <optgroup v-for="g in navGroups" :key="g.label" :label="g.label">
        <option v-for="it in g.items" :key="it.key" :value="it.key">{{ it.label }}</option>
      </optgroup>
    </select>

    <div class="set-content">
      <header class="set-head">
        <h2>{{ current.label }}</h2>
        <p>{{ current.desc }}</p>
      </header>

      <!-- ───────── Geral ───────── -->
      <template v-if="section === 'organizacao'">
        <section class="set-card">
          <div class="set-card-title">Identidade</div>
          <div class="hd-field">
            <label class="hd-label">Nome do Agrupamento</label>
            <input class="hd-input" v-model="general.org_name" placeholder="Agrupamento de Escolas Eça de Queirós" />
          </div>
          <div class="hd-field">
            <label class="hd-label">Logotipo</label>
            <div class="logo-row">
              <div class="logo-preview">
                <img v-if="general.logo_url" :src="general.logo_url" alt="Logotipo" />
                <span v-else class="material-icons">image</span>
              </div>
              <div>
                <input type="file" accept=".png,.jpg,.jpeg,.svg,.webp,image/png,image/jpeg,image/svg+xml,image/webp" @change="onLogoPicked" />
                <p class="hd-hint">PNG, JPG, SVG ou WEBP até 2 MB. Também é usado como ícone do separador do browser.</p>
              </div>
            </div>
          </div>
          <div class="set-actions">
            <span v-if="saved" class="set-ok">Guardado!</span>
            <button class="hd-btn hd-btn-primary" @click="saveGeneral"><span class="material-icons">save</span> Guardar</button>
          </div>
        </section>
        <section class="set-card">
          <div class="set-row">
            <div>
              <div class="set-card-title">Design do Painel inicial e do login</div>
              <div class="set-desc">Aplica-se a todos os utilizadores. Muda na hora.</div>
            </div>
            <div class="design-choice" role="radiogroup" aria-label="Design do Painel inicial e do login">
              <button type="button" :class="{ selected: uiDesign === 'modern' }" @click="changeDesign('modern')">Moderno</button>
              <button type="button" :class="{ selected: uiDesign === 'classic' }" @click="changeDesign('classic')">Clássico</button>
            </div>
          </div>
          <p v-if="designError" class="set-err">{{ designError }}</p>
        </section>
        <section class="set-card">
          <div class="set-row">
            <div>
              <div class="set-card-title">Modo escuro</div>
              <div class="set-desc">
                Como fica a aplicação para quem ativa o modo escuro (botão <span class="material-icons" style="font-size:14px;vertical-align:-2px">dark_mode</span> no topo).
                O <strong>preto puro</strong> (true black) usa fundo totalmente preto: mais contraste e poupa bateria em ecrãs OLED (iPhone, alguns iPad e Android).
              </div>
            </div>
            <div class="design-choice" role="radiogroup" aria-label="Estilo do modo escuro">
              <button type="button" :class="{ selected: darkStyle === 'grey' }" @click="changeDarkStyle('grey')">Cinzento escuro</button>
              <button type="button" :class="{ selected: darkStyle === 'black' }" @click="changeDarkStyle('black')">Preto puro</button>
            </div>
          </div>
          <div class="dark-previews">
            <div class="dark-preview grey" :class="{ selected: darkStyle === 'grey' }"><span></span><span></span><span></span></div>
            <div class="dark-preview black" :class="{ selected: darkStyle === 'black' }"><span></span><span></span><span></span></div>
          </div>
        </section>
      </template>

      <!-- ───────── Tickets ───────── -->
      <template v-if="section === 'categorias'">
        <section class="set-card">
          <div class="set-row" style="margin-bottom:14px">
            <div>
              <div class="set-card-title">Categorias</div>
              <div class="set-desc">O email de cada categoria recebe um aviso quando é criado um ticket nela.</div>
            </div>
            <button class="hd-btn hd-btn-primary" @click="showNewCat = true"><span class="material-icons">add</span> Nova categoria</button>
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
        </section>
        <section class="set-card">
          <div class="set-row">
            <div>
              <div class="set-card-title">Avisos de categoria</div>
              <div class="set-desc">Mostra uma janela de aviso ao escolher uma categoria que tenha aviso configurado.</div>
            </div>
            <div class="hd-toggle-wrap" @click="toggleCategoryWarnings"><div class="hd-toggle-track" :class="{ on: categoryWarningsEnabled }"><div class="hd-toggle-thumb"></div></div></div>
          </div>
        </section>
      </template>

      <template v-if="section === 'escolas'">
        <section class="set-card">
          <div class="set-row" style="margin-bottom:14px">
            <div class="set-card-title">Escolas do Agrupamento</div>
            <button class="hd-btn hd-btn-primary" @click="showNewSchool = true"><span class="material-icons">add</span> Nova escola</button>
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
        </section>
      </template>

      <template v-if="section === 'encaminhamento'">
        <section class="set-card">
          <div class="set-card-title">Regras</div>
          <p class="set-desc" style="margin-bottom:14px">Quando um ticket é criado, a primeira regra compatível (menor número de ordem) atribui automaticamente o grupo e/ou o responsável.</p>
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
        </section>
      </template>

      <template v-if="section === 'empresa'">
        <section class="set-card">
          <div class="set-card-title">Empresa de apoio informático</div>
          <p class="set-desc" style="margin-bottom:14px">Usada quando um técnico reporta um ticket à empresa ("Enviar para empresa de apoio").</p>
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
          <div class="set-actions">
            <span v-if="saved" class="set-ok">Guardado!</span>
            <button class="hd-btn hd-btn-primary" @click="saveGeneral"><span class="material-icons">save</span> Guardar</button>
          </div>
        </section>
      </template>

      <!-- ───────── Comunicação ───────── -->
      <SupportChatSettings v-if="section === 'apoio'" @changed="loadSupportFlag" />
      <TeamsSettings v-if="section === 'teams'" />

      <template v-if="section === 'email'">
        <section class="set-card">
          <div class="set-card-title">Envio de email</div>
          <p class="set-desc">O servidor de email (SMTP) e a caixa de correio que recebe as respostas são configurados no ficheiro <code>app.env</code> do servidor. Use o teste para confirmar que está a funcionar.</p>
          <div class="set-actions" style="justify-content:flex-start">
            <button class="hd-btn hd-btn-outline" :disabled="testingSmtp" @click="testSmtpNow">
              <span class="material-icons">send</span> {{ testingSmtp ? 'A enviar...' : 'Enviar email de teste para mim' }}
            </button>
            <span v-if="smtpTestResult" :class="smtpTestOk ? 'set-ok' : 'set-err'">{{ smtpTestResult }}</span>
          </div>
        </section>
        <section class="set-card">
          <div class="set-card-title">Notificações no telemóvel e no computador</div>
          <p class="set-desc">Envia uma notificação de teste para este dispositivo. Primeiro ative as notificações na campainha, no topo da página.</p>
          <div style="display:flex;flex-direction:column;gap:8px;margin-top:12px">
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
        </section>
        <section class="set-card">
          <div class="set-card-title">Quem recebe as sugestões</div>
          <p class="set-desc" style="margin-bottom:10px">Quando alguém envia uma sugestão, é enviado um email para estes endereços (separe vários com vírgula).</p>
          <input class="hd-input" v-model="suggestionEmailsRaw" placeholder="admin@escola.pt, diretor@escola.pt" />
          <div class="set-actions">
            <span v-if="savedEmail" class="set-ok">Guardado!</span>
            <button class="hd-btn hd-btn-primary" @click="saveEmailSettings"><span class="material-icons">save</span> Guardar</button>
          </div>
        </section>
      </template>

      <!-- ───────── Acesso e login ───────── -->
      <template v-if="section === 'login'">
        <section class="set-card">
          <div class="set-row">
            <div>
              <div class="set-card-title">Aviso no ecrã de login</div>
              <div class="set-desc">Janela mostrada a quem abre a página de login, antes de entrar.</div>
            </div>
            <div class="hd-toggle-wrap" @click="toggleLoginNotice"><div class="hd-toggle-track" :class="{ on: loginNoticeEnabled }"><div class="hd-toggle-thumb"></div></div></div>
          </div>
          <div :style="{ opacity: loginNoticeEnabled ? 1 : 0.5 }" style="margin-top:12px">
            <textarea class="hd-textarea" v-model="loginNoticeText" rows="4" placeholder="Texto do aviso"></textarea>
            <div class="set-actions">
              <span v-if="loginNoticeSaved" class="set-ok">Guardado!</span>
              <button class="hd-btn hd-btn-outline" @click="saveLoginNotice"><span class="material-icons">save</span> Guardar texto</button>
            </div>
          </div>
          <p v-if="loginNoticeError" class="set-err">{{ loginNoticeError }}</p>
        </section>
        <section class="set-card">
          <div class="set-card-title">"Não tenho acesso ao mail institucional"</div>
          <p class="set-desc" style="margin-bottom:10px">Endereço que recebe os pedidos feitos neste botão do ecrã de login.</p>
          <div class="hd-row" style="gap:10px;align-items:center;flex-wrap:wrap">
            <input class="hd-input" v-model="noAccessContactEmail" type="email" placeholder="helpdesk_aeeq@queiroz.pt" style="max-width:340px" />
            <button class="hd-btn hd-btn-outline" @click="saveNoAccessContact"><span class="material-icons">save</span> Guardar</button>
            <span v-if="noAccessContactSaved" class="set-ok">Guardado!</span>
          </div>
          <p v-if="noAccessContactError" class="set-err">{{ noAccessContactError }}</p>
        </section>
        <section class="set-card set-info">
          <span class="material-icons">info</span>
          <div>
            <div class="set-card-title">Contas e autenticação</div>
            <p class="set-desc">A entrada com a conta da escola (Microsoft Entra ID) e o Active Directory são configurados no ficheiro <code>app.env</code> do servidor. As unidades organizativas sincronizadas e os papéis gerem-se em <router-link to="/admin/users">Utilizadores</router-link>.</p>
          </div>
        </section>
      </template>

      <template v-if="section === 'demo'">
        <section class="set-card">
          <div class="set-row">
            <div>
              <div class="set-card-title">Modo demonstração</div>
              <div class="set-desc">Mostra "Entrar em modo demo" no ecrã de login, para experimentar sem conta.</div>
            </div>
            <div class="hd-toggle-wrap" @click="toggleDemoMode"><div class="hd-toggle-track" :class="{ on: demoEnabled }"><div class="hd-toggle-thumb"></div></div></div>
          </div>
          <div v-if="demoEnabled" class="demo-settings" style="margin-top:12px">
          <div style="font-size:12px;font-weight:600;margin-bottom:6px">Perfis disponíveis</div>
          <div class="hd-row" style="gap:16px;margin-bottom:10px">
            <label v-for="p in demoProfileOptions" :key="p.role" class="demo-profile-opt">
              <input type="checkbox" :checked="demoProfiles.includes(p.role)" @change="toggleDemoProfile(p.role)" />
              {{ p.label }}
            </label>
          </div>
          <p class="demo-warning">
            <span class="material-icons" style="font-size:16px">warning</span>
            <span>O modo demo usa a base de dados real: os pedidos criados em demo são tickets verdadeiros. Por segurança só existe o perfil
            <strong>Docente</strong> (os perfis Técnico e Administrador davam acesso aos dados reais a qualquer visitante). Desative quando já não for preciso.</span>
          </p>
        </div>
          <p v-if="demoError" class="set-err">{{ demoError }}</p>
        </section>
        <section class="set-card">
          <div class="set-row">
            <div>
              <div class="set-card-title">Mostrar tickets e mensagens do modo demo</div>
              <div class="set-desc">Desligado: o que for criado em modo demo fica escondido dos utilizadores reais.</div>
            </div>
            <div class="hd-toggle-wrap" @click="toggleDemoContent"><div class="hd-toggle-track" :class="{ on: demoContentVisible }"><div class="hd-toggle-thumb"></div></div></div>
          </div>
        </section>
      </template>

      <!-- ───────── Conteúdos ───────── -->
      <template v-if="section === 'conhecimento'">
        <section class="set-card">
          <div class="set-row">
            <div>
              <div class="set-card-title">Mostrar a Base de conhecimento</div>
              <div class="set-desc">Artigos visíveis a todos para resolver sozinhos os problemas mais comuns.</div>
            </div>
            <div class="hd-toggle-wrap" @click="toggleKnowledge"><div class="hd-toggle-track" :class="{ on: knowledgeEnabled }"><div class="hd-toggle-thumb"></div></div></div>
          </div>
        </section>
        <section class="set-card">
          <div class="set-card-title">Artigos</div>
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
        <div class="hd-row" style="gap:8px">
          <button v-if="editingArticleId" class="hd-btn hd-btn-outline" @click="cancelEditArticle">Cancelar</button>
          <button class="hd-btn hd-btn-primary" @click="addArticle" :disabled="!newArticle.title || !newArticle.body">
            {{ editingArticleId ? 'Guardar alterações' : 'Adicionar artigo' }}
          </button>
        </div>
      </div>

      <table class="hd-table">
        <thead><tr><th>TÍTULO</th><th>CATEGORIA</th><th>ESTADO</th><th></th></tr></thead>
        <tbody>
          <tr v-for="article in articles" :key="article.id">
            <td style="font-weight:700">{{ article.title }}</td>
            <td>{{ article.category?.name || '—' }}</td>
            <td>{{ article.is_published ? 'Publicado' : 'Rascunho' }}</td>
            <td style="white-space:nowrap">
              <button class="hd-icon-btn" @click="editArticle(article)" title="Editar">
                <span class="material-icons" style="font-size:15px">edit</span>
              </button>
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
        </section>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { confirmDialog, errorMessage, notifyError } from '../../utils/feedback'
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createCategory, createKnowledgeArticle, createRoutingRule, createSchool as apiCreateSchool, deleteCategory as apiDeleteCategory, deleteKnowledgeArticle, deleteRoutingRule, updateKnowledgeArticle, deleteSchool as apiDeleteSchool, getCategories, getKnowledgeArticles, getRoutingRules, getSchools, updateCategory as apiUpdateCategory, testSmtp, testPush as apiTestPush } from '../../api/tickets'
import { applyDarkStyle, type DarkStyle } from '../../utils/darkStyle'
import { getPublicSettings, updateDarkStyle, updateDemoModeSettings, updateDesignSettings, updateFeatureSettings, updateLoginNoticeSettings, updateNoAccessContactSettings, updateSettings } from '../../api/settings'
import { setUiDesign, type UiDesign } from '../../composables/useUiDesign'
import { api } from '../../boot/axios'
import SupportChatSettings from '../../components/SupportChatSettings.vue'
import TeamsSettings from '../../components/TeamsSettings.vue'
import { getGroups, getUsers } from '../../api/users'

const route = useRoute()
const router = useRouter()

// Grouped sections of the settings page (the key is kept in the URL: /admin/settings?s=apoio)
const supportEnabled = ref(false)
const teamsConfigured = ref(false)
const navGroups = computed(() => [
  { label: 'Geral', items: [
    { key: 'organizacao', label: 'Organização e aspeto', icon: 'apartment', desc: 'Nome, logotipo, design e modo escuro.' },
  ] },
  { label: 'Tickets', items: [
    { key: 'categorias', label: 'Categorias e prazos', icon: 'category', desc: 'Categorias dos pedidos, tempos de resposta e emails de aviso.' },
    { key: 'escolas', label: 'Escolas', icon: 'account_balance', desc: 'Escolas que os utilizadores escolhem ao abrir um ticket.' },
    { key: 'encaminhamento', label: 'Encaminhamento', icon: 'alt_route', desc: 'Quem fica responsável por cada tipo de pedido.' },
    { key: 'empresa', label: 'Empresa de apoio', icon: 'handshake', desc: 'Empresa externa para onde se reportam os tickets.' },
  ] },
  { label: 'Comunicação', items: [
    { key: 'apoio', label: 'Apoio ao vivo', icon: 'support_agent', desc: 'Balão de chat para os docentes falarem com a equipa TIC em tempo real.',
      badge: { text: supportEnabled.value ? 'Ligado' : 'Desligado', cls: supportEnabled.value ? 'on' : '' } },
    { key: 'teams', label: 'Microsoft Teams', icon: 'groups', desc: 'Avisos do helpdesk num canal do Teams.',
      badge: teamsConfigured.value ? { text: 'Ligado', cls: 'on' } : null },
    { key: 'email', label: 'Email e notificações', icon: 'mail', desc: 'Testes de email e de notificações, e quem recebe as sugestões.' },
  ] },
  { label: 'Acesso', items: [
    { key: 'login', label: 'Ecrã de login', icon: 'login', desc: 'Aviso inicial e contacto para quem não tem acesso ao mail institucional.' },
    { key: 'demo', label: 'Modo demonstração', icon: 'science', desc: 'Entrada sem conta para experimentar a aplicação.',
      badge: demoEnabled.value ? { text: 'Ligado', cls: 'warn' } : null },
  ] },
  { label: 'Conteúdos', items: [
    { key: 'conhecimento', label: 'Base de conhecimento', icon: 'menu_book', desc: 'Artigos de ajuda visíveis a todos.' },
  ] },
])
const allSections = computed(() => navGroups.value.flatMap((g) => g.items))
const section = ref(String(route.query.s || 'organizacao'))
const current = computed(() => allSections.value.find((it) => it.key === section.value) ?? allSections.value[0])
function go(key: string) {
  section.value = key
  saved.value = false
  router.replace({ query: { s: key } })
}
async function loadSupportFlag() {
  try {
    const s: any = await getPublicSettings()
    supportEnabled.value = s.support_chat_enabled === true
    const t = await api.get('/api/v1/settings/teams')
    teamsConfigured.value = !!t.data.configured
  } catch { /* ignore */ }
}
const saved = ref(false)
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
const loginNoticeEnabled = ref(false)
const loginNoticeText = ref('')
const loginNoticeSaved = ref(false)
const loginNoticeError = ref('')
const demoEnabled = ref(false)
const demoProfiles = ref<string[]>(['teacher'])
const demoError = ref('')
const demoContentVisible = ref(false)
const demoProfileOptions = [
  { role: 'teacher', label: 'Docente' },
]
const uiDesign = ref<UiDesign>('modern')
const darkStyle = ref<DarkStyle>('grey')
async function changeDarkStyle(style: DarkStyle) {
  if (style === darkStyle.value) return
  const previous = darkStyle.value
  darkStyle.value = style
  applyDarkStyle(style)
  try {
    await updateDarkStyle(style)
  } catch (e) {
    darkStyle.value = previous
    applyDarkStyle(previous)
    notifyError(e, 'Não foi possível guardar o estilo do modo escuro.')
  }
}
const designError = ref('')
const noAccessContactEmail = ref('')
const noAccessContactSaved = ref(false)
const noAccessContactError = ref('')

const general = ref({ org_name: '', logo_url: '', support_provider_name: 'Empresa de apoio informático', support_provider_email: '' })
const suggestionEmailsRaw = ref('')
const savedEmail = ref(false)


const newCat = ref({ name: '', description: '', email_to: '', icon: 'help', color: '#3D52D5', sla_hours: 48 })
const newSchool = ref({ name: '', short_name: '', address: '' })
const newRoute = ref({ category_id: '', school_id: '', group_id: '', assignee_id: '', priority: 100 })
const newArticle = ref({ title: '', body: '', category_id: '', is_published: true })

onMounted(async () => {
  loadSupportFlag()
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
    loginNoticeEnabled.value = settings.login_notice_enabled === true
    loginNoticeText.value = settings.login_notice_text || ''
    noAccessContactEmail.value = settings.no_access_contact_email || ''
    uiDesign.value = settings.ui_design === 'classic' ? 'classic' : 'modern'
    darkStyle.value = settings.dark_style === 'black' ? 'black' : 'grey'
    demoEnabled.value = settings.demo_mode_enabled === true
    demoContentVisible.value = settings.demo_content_visible === true
    demoProfiles.value = settings.demo_profiles?.length ? settings.demo_profiles : ['teacher']
    suggestionEmailsRaw.value = (settings.suggestion_emails || []).join(', ')
    supportEnabled.value = (settings as any).support_chat_enabled === true
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
    setTimeout(() => { saved.value = false }, 3000)
  } catch (e) {
    notifyError(e, 'Não foi possível guardar as configurações.')
  }
}

async function toggleKnowledge() {
  const next = !knowledgeEnabled.value
  try {
    const saved = await updateFeatureSettings({ knowledge_enabled: next, category_warnings_enabled: categoryWarningsEnabled.value })
    knowledgeEnabled.value = saved.knowledge_enabled
  } catch (e) {
    notifyError(e, 'Não foi possível alterar a base de conhecimento.')
  }
}

async function toggleCategoryWarnings() {
  const next = !categoryWarningsEnabled.value
  try {
    const saved = await updateFeatureSettings({ knowledge_enabled: knowledgeEnabled.value, category_warnings_enabled: next })
    categoryWarningsEnabled.value = saved.category_warnings_enabled
  } catch (e) {
    notifyError(e, 'Não foi possível alterar os avisos das categorias.')
  }
}

async function toggleLoginNotice() {
  const next = !loginNoticeEnabled.value
  loginNoticeError.value = ''
  try {
    const saved = await updateLoginNoticeSettings({ enabled: next, text: loginNoticeText.value })
    loginNoticeEnabled.value = saved.login_notice_enabled
    loginNoticeText.value = saved.login_notice_text
  } catch (e: any) {
    loginNoticeError.value = errorMessage(e, 'Erro ao gravar.')
  }
}

async function saveLoginNotice() {
  loginNoticeSaved.value = false
  loginNoticeError.value = ''
  try {
    const saved = await updateLoginNoticeSettings({ enabled: loginNoticeEnabled.value, text: loginNoticeText.value })
    loginNoticeEnabled.value = saved.login_notice_enabled
    loginNoticeText.value = saved.login_notice_text
    loginNoticeSaved.value = true
    setTimeout(() => { loginNoticeSaved.value = false }, 3000)
  } catch (e: any) {
    loginNoticeError.value = errorMessage(e, 'Erro ao gravar.')
  }
}

async function saveDemoMode(enabled: boolean, profiles: string[], contentVisible?: boolean) {
  demoError.value = ''
  try {
    const saved = await updateDemoModeSettings({ enabled, profiles, content_visible: contentVisible })
    demoEnabled.value = saved.demo_mode_enabled
    demoProfiles.value = saved.demo_profiles
    demoContentVisible.value = saved.demo_content_visible === true
  } catch (e: any) {
    demoError.value = errorMessage(e, 'Erro ao gravar.')
  }
}

function toggleDemoContent() {
  saveDemoMode(demoEnabled.value, demoProfiles.value, !demoContentVisible.value)
}

function toggleDemoMode() {
  saveDemoMode(!demoEnabled.value, demoProfiles.value)
}

function toggleDemoProfile(role: string) {
  const next = demoProfiles.value.includes(role)
    ? demoProfiles.value.filter(r => r !== role)
    : [...demoProfiles.value, role]
  if (!next.length) {
    demoError.value = 'Escolha pelo menos um perfil para o modo demo.'
    return
  }
  saveDemoMode(demoEnabled.value, next)
}

async function changeDesign(design: UiDesign) {
  if (design === uiDesign.value) return
  designError.value = ''
  try {
    const saved = await updateDesignSettings(design)
    uiDesign.value = saved.ui_design
    setUiDesign(saved.ui_design)
  } catch (e: any) {
    designError.value = errorMessage(e, 'Erro ao gravar.')
  }
}

async function saveNoAccessContact() {
  noAccessContactSaved.value = false
  noAccessContactError.value = ''
  try {
    const saved = await updateNoAccessContactSettings({ email: noAccessContactEmail.value })
    noAccessContactEmail.value = saved.no_access_contact_email
    noAccessContactSaved.value = true
    setTimeout(() => { noAccessContactSaved.value = false }, 3000)
  } catch (e: any) {
    noAccessContactError.value = errorMessage(e, 'Erro ao gravar.')
  }
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
    smtpTestResult.value = errorMessage(e, 'Erro ao enviar email de teste')
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
    pushTestResult.value = errorMessage(e, 'Erro ao enviar notificação push')
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
  } catch (e) {
    notifyError(e, 'Não foi possível guardar os emails.')
  }
}


async function createCat() {
  try {
    const cat = await createCategory({ ...newCat.value })
    categories.value.push(cat)
    showNewCat.value = false
    newCat.value = { name: '', description: '', email_to: '', icon: 'help', color: '#3D52D5', sla_hours: 48 }
  } catch (e) {
    notifyError(e, 'Não foi possível criar a categoria.')
  }
}

async function saveCategoryEmail(cat: any) {
  try {
    const updated = await apiUpdateCategory(cat.id, { email_to: cat.email_to || '' })
    const idx = categories.value.findIndex(c => c.id === cat.id)
    if (idx !== -1) categories.value[idx] = { ...categories.value[idx], ...updated }
  } catch (e) {
    notifyError(e, 'Não foi possível guardar o email da categoria.')
  }
}

async function deleteCategory(id: number) {
  if (!(await confirmDialog('Eliminar esta categoria?', { ok: 'Eliminar', danger: true }))) return
  try {
    await apiDeleteCategory(id)
    categories.value = categories.value.filter(c => c.id !== id)
  } catch (e) {
    notifyError(e, 'Não foi possível eliminar a categoria.')
  }
}

async function createSchool() {
  try {
    const school = await apiCreateSchool({ ...newSchool.value })
    schools.value.push(school)
    showNewSchool.value = false
    newSchool.value = { name: '', short_name: '', address: '' }
  } catch (e) {
    notifyError(e, 'Não foi possível criar a escola.')
  }
}

async function deleteSchool(id: number) {
  if (!(await confirmDialog('Eliminar esta escola? Os tickets desta escola ficam sem escola.', { ok: 'Eliminar', danger: true }))) return
  try {
    await apiDeleteSchool(id)
    schools.value = schools.value.filter(s => s.id !== id)
  } catch (e) {
    notifyError(e, 'Não foi possível eliminar a escola.')
  }
}

async function addRoute() {
  let route
  try {
    route = await createRoutingRule({
      category_id: newRoute.value.category_id ? Number(newRoute.value.category_id) : null,
      school_id: newRoute.value.school_id ? Number(newRoute.value.school_id) : null,
      group_id: newRoute.value.group_id ? Number(newRoute.value.group_id) : null,
      assignee_id: newRoute.value.assignee_id ? Number(newRoute.value.assignee_id) : null,
      priority: Number(newRoute.value.priority) || 100,
    })
  } catch (e) {
    notifyError(e, 'Não foi possível criar a regra.')
    return
  }
  routingRules.value.push(route)
  routingRules.value.sort((a, b) => a.priority - b.priority)
  newRoute.value = { category_id: '', school_id: '', group_id: '', assignee_id: '', priority: 100 }
}

async function removeRoute(id: number) {
  if (!(await confirmDialog('Eliminar esta regra?', { ok: 'Eliminar', danger: true }))) return
  try {
    await deleteRoutingRule(id)
  } catch (e) {
    notifyError(e, 'Não foi possível eliminar a regra.')
    return
  }
  routingRules.value = routingRules.value.filter(r => r.id !== id)
}

const editingArticleId = ref<number | null>(null)

async function addArticle() {
  const payload = {
    title: newArticle.value.title,
    body: newArticle.value.body,
    category_id: newArticle.value.category_id ? Number(newArticle.value.category_id) : null,
    is_published: newArticle.value.is_published,
  }
  try {
    if (editingArticleId.value) {
      const updated = await updateKnowledgeArticle(editingArticleId.value, payload)
      const idx = articles.value.findIndex(a => a.id === updated.id)
      if (idx !== -1) articles.value[idx] = updated
    } else {
      articles.value.unshift(await createKnowledgeArticle(payload))
    }
  } catch (e) {
    notifyError(e, 'Não foi possível guardar o artigo.')
    return
  }
  cancelEditArticle()
}

function editArticle(article: any) {
  editingArticleId.value = article.id
  newArticle.value = {
    title: article.title,
    body: article.body,
    category_id: article.category_id ? String(article.category_id) : '',
    is_published: article.is_published,
  }
}

function cancelEditArticle() {
  editingArticleId.value = null
  newArticle.value = { title: '', body: '', category_id: '', is_published: true }
}

async function removeArticle(id: number) {
  if (!(await confirmDialog('Eliminar este artigo?', { ok: 'Eliminar', danger: true }))) return
  try {
    await deleteKnowledgeArticle(id)
  } catch (e) {
    notifyError(e, 'Não foi possível eliminar o artigo.')
    return
  }
  articles.value = articles.value.filter(a => a.id !== id)
}

</script>

<style scoped>
/* Layout: grouped navigation on the left, section cards on the right */
.settings-page { display: grid; grid-template-columns: 260px minmax(0, 1fr); gap: 28px; align-items: start; }
.set-nav { position: sticky; top: 16px; display: flex; flex-direction: column; gap: 2px; padding: 10px; background: var(--c-surface); border: 1px solid var(--c-border); border-radius: 16px; }
.set-nav-group { font-size: 10.5px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; color: var(--c-muted); padding: 12px 10px 4px; }
.set-nav-group:first-child { padding-top: 4px; }
.set-nav-item { display: flex; align-items: center; gap: 10px; width: 100%; padding: 8px 10px; border: 0; border-radius: 10px; background: transparent; color: var(--c-text); font-size: 13.5px; font-weight: 600; text-align: left; cursor: pointer; }
.set-nav-item .material-icons { font-size: 18px; color: var(--c-muted); }
.set-nav-item:hover { background: var(--c-bg); }
.set-nav-item.active { background: var(--c-primary-soft); color: var(--c-primary); }
.set-nav-item.active .material-icons { color: var(--c-primary); }
.set-nav-badge { margin-left: auto; font-size: 10px; font-weight: 800; padding: 1px 7px; border-radius: 999px; background: var(--c-bg); color: var(--c-muted); border: 1px solid var(--c-border); }
.set-nav-badge.on { background: rgba(34, 197, 94, .12); color: #15803D; border-color: rgba(34, 197, 94, .35); }
.set-nav-badge.warn { background: rgba(245, 158, 11, .14); color: #B45309; border-color: rgba(245, 158, 11, .4); }
.dark .set-nav-badge.on { color: #4ADE80; }
.set-nav-mobile { display: none; }
.set-content { min-width: 0; max-width: 980px; display: flex; flex-direction: column; gap: 16px; }
.set-head h2 { margin: 0; font-size: 22px; font-weight: 800; }
.set-head p { margin: 4px 0 0; color: var(--c-muted); font-size: 13.5px; }
.set-card { background: var(--c-surface); border: 1px solid var(--c-border); border-radius: 16px; padding: 22px 24px; }
.set-card .hd-field { margin-bottom: 16px; }
.set-card-title { font-weight: 700; font-size: 14.5px; }
.set-card > .set-card-title:first-child { margin-bottom: 12px; }
.set-card > .set-card-title:first-child + .set-desc { margin-top: -8px; }
.set-nav-item > span:nth-child(2) { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.set-desc { font-size: 12.5px; color: var(--c-muted); margin: 3px 0 0; line-height: 1.5; }
.set-desc code { font-size: 12px; background: var(--c-bg); border: 1px solid var(--c-border); border-radius: 5px; padding: 0 4px; }
.set-row { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.set-actions { display: flex; justify-content: flex-end; align-items: center; gap: 12px; margin-top: 16px; flex-wrap: wrap; }
.set-actions .material-icons, .set-row .hd-btn .material-icons { font-size: 16px; }
.set-ok { font-size: 13px; color: #16A34A; }
.set-err { font-size: 12.5px; color: #DC2626; margin: 8px 0 0; }
.set-info { display: flex; gap: 12px; background: var(--c-bg); }
.set-info > .material-icons { color: var(--c-primary); }
.logo-row { display: flex; gap: 16px; align-items: center; flex-wrap: wrap; }
.logo-row > div:last-child { min-width: 0; flex: 1 1 200px; }
.logo-row input[type=file] { max-width: 100%; }
.logo-preview { width: 120px; height: 64px; border: 1px dashed var(--c-border); border-radius: 12px; display: grid; place-items: center; background: var(--c-bg); flex-shrink: 0; }
.logo-preview img { max-width: 108px; max-height: 52px; object-fit: contain; }
.logo-preview .material-icons { color: var(--c-muted); }
@media (max-width: 900px) {
  .settings-page { grid-template-columns: 1fr; gap: 14px; }
  .set-nav { display: none; }
  .set-nav-mobile { display: block; }
  .set-card { padding: 18px; }
  .set-row { align-items: flex-start; }
}

.demo-settings {
  padding: 12px 14px;
  margin-bottom: 8px;
  border: 1px solid var(--c-border);
  border-radius: 10px;
}
.demo-profile-opt {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  cursor: pointer;
}
.demo-warning {
  display: flex;
  gap: 8px;
  margin: 0;
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(245, 158, 11, .1);
  border: 1px solid rgba(245, 158, 11, .3);
  color: #92400E;
  font-size: 12px;
  line-height: 1.45;
}
.dark .demo-warning { color: #FCD34D; }
.dark-previews { display: flex; gap: 12px; margin-top: 14px; }
.dark-preview { width: 120px; height: 72px; border-radius: 10px; padding: 10px; display: flex; flex-direction: column; gap: 6px; border: 2px solid transparent; }
.dark-preview.selected { border-color: var(--c-primary); }
.dark-preview span { display: block; height: 10px; border-radius: 4px; }
.dark-preview.grey { background: #0D111A; }
.dark-preview.grey span { background: #171C29; border: 1px solid #293247; }
.dark-preview.black { background: #000; }
.dark-preview.black span { background: #0B0B0C; border: 1px solid #232428; }
.dark-preview span:first-child { width: 60%; background: #6D7DFF; border: 0; }
.design-choice {
  display: inline-flex;
  overflow: hidden;
  flex-shrink: 0;
  border: 1px solid var(--c-border);
  border-radius: 8px;
  background: var(--c-bg);
}
.design-choice button {
  min-width: 84px;
  padding: 6px 12px;
  border: 0;
  background: transparent;
  color: var(--c-muted);
  cursor: pointer;
  font: 700 12px var(--font-sans);
}
.design-choice button.selected {
  background: var(--c-primary);
  color: #fff;
}
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
