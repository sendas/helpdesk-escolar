<template>
  <div class="hd-page about-page">

    <!-- Hero banner -->
    <div class="hero">
      <div class="hero__icon-wrap">
        <q-icon name="support_agent" size="48px" color="white" />
      </div>
      <div class="hero__title">Helpdesk Escolar</div>
      <q-badge class="hero__badge">v{{ APP_VERSION }}</q-badge>
      <div class="hero__subtitle">
        Sistema de gestão de pedidos de suporte e assistência técnica
      </div>
    </div>

    <div class="about-body">

      <!-- Autoria -->
      <div class="hd-card about-card">
        <div class="about-author-row">
          <div class="about-avatar">PS</div>
          <div>
            <div class="about-author-name">Pedro Sendas de Moura Pereira</div>
            <div class="about-author-role">Docente · Grupo 550 — Informática</div>
          </div>
        </div>
        <p class="about-text">
          Esta aplicação foi concebida, desenhada e desenvolvida em maio de 2026 por Pedro Sendas de Moura Pereira,
          professor de Informática do Agrupamento. A ideia surgiu da necessidade prática de centralizar todos os
          pedidos de apoio técnico — dos docentes, funcionários e direção — num único sistema, eliminando a dispersão
          por emails, mensagens e contactos informais que tornavam difícil acompanhar e priorizar as ocorrências.
        </p>
      </div>

      <!-- Método de criação -->
      <div class="hd-card about-card">
        <div class="about-section-title">
          <span class="material-icons" style="font-size:20px;color:#3D52D5">auto_awesome</span>
          Método de criação — IA como co-piloto
        </div>

        <p class="about-text" style="margin-bottom:16px">
          O Helpdesk Escolar foi desenvolvido através de uma metodologia de <strong>programação assistida por inteligência artificial</strong>,
          em que o docente assumiu o papel de arquiteto e produto — definindo requisitos, validando decisões e testando
          cada funcionalidade — enquanto dois modelos de linguagem funcionaram como co-pilotos de desenvolvimento.
        </p>

        <div class="about-tools">
          <div class="about-tool-card">
            <div class="about-tool-header" style="background:linear-gradient(135deg,#1a1a2e,#16213e)">
              <span style="font-size:22px">✦</span>
              <div>
                <div style="font-weight:700;font-size:14px">Claude Code</div>
                <div style="font-size:11px;opacity:.7">Anthropic · claude-sonnet-4</div>
              </div>
            </div>
            <p class="about-tool-desc">
              Responsável pela maior parte da arquitetura e da implementação. Através do terminal (CLI),
              gerou e editou diretamente os ficheiros do projeto — modelos SQLAlchemy, endpoints FastAPI,
              componentes Vue, lógica de autenticação LDAP/Azure AD, notificações Web Push
              e toda a configuração Docker. A capacidade de raciocinar sobre múltiplos
              ficheiros ao mesmo tempo e manter contexto ao longo de sessões longas foi determinante.
            </p>
          </div>

          <div class="about-tool-card">
            <div class="about-tool-header" style="background:linear-gradient(135deg,#10a37f,#0d8a6c)">
              <span style="font-size:22px">⬡</span>
              <div>
                <div style="font-weight:700;font-size:14px">ChatGPT / Codex</div>
                <div style="font-size:11px;opacity:.7">OpenAI · GPT-4o</div>
              </div>
            </div>
            <p class="about-tool-desc">
              Utilizado para exploração rápida de alternativas, revisão de algoritmos específicos e
              segunda opinião sobre escolhas de design. Em particular, foi consultado na fase inicial
              de definição da stack tecnológica, na análise de opções para autenticação híbrida e
              na revisão da integração VAPID/Web Push. A complementaridade entre os dois modelos
              permitiu cruzar perspectivas e chegar a soluções mais robustas.
            </p>
          </div>
        </div>

        <div class="about-workflow">
          <div class="about-workflow-title">Fluxo de trabalho</div>
          <ol class="about-steps">
            <li><strong>Levantamento de requisitos</strong> — definição das funcionalidades necessárias com base no dia-a-dia do agrupamento: gestão de tickets, notificações, autenticação com contas Microsoft, mobile-first.</li>
            <li><strong>Desenho da arquitetura</strong> — escolha da stack (FastAPI + SQLite/PostgreSQL + Quasar PWA) e estrutura de diretórios gerada assistida por IA.</li>
            <li><strong>Desenvolvimento iterativo</strong> — cada funcionalidade foi pedida em linguagem natural, o código gerado foi revisto, testado em ambiente Docker local e refinado em ciclos curtos de 10–30 minutos.</li>
            <li><strong>Validação em contexto real</strong> — a aplicação foi testada com utilizadores do agrupamento durante o seu desenvolvimento, incorporando feedback imediato (layout móvel, safe area iOS, fluxos de autenticação).</li>
            <li><strong>Manutenção e evolução</strong> — novas funcionalidades continuam a ser adicionadas com o mesmo método: descrição do problema → código gerado e revisto → deploy e teste.</li>
          </ol>
        </div>

        <div class="about-quote">
          "A IA não substituiu o conhecimento técnico — amplificou-o. Saber o que pedir, avaliar
          o que é gerado e adaptar ao contexto específico da escola continuou a ser o trabalho do docente."
        </div>
      </div>

      <!-- Historial de versões -->
      <div class="hd-card about-card">
        <div class="about-section-title">
          <span class="material-icons" style="font-size:20px;color:#3D52D5">tag</span>
          Historial de versões
        </div>

        <q-timeline color="primary" layout="comfortable" class="q-mt-xs">
          <q-timeline-entry
            v-for="(entry, idx) in visibleEntries"
            :key="entry.version"
            :icon="idx === 0 ? 'rocket_launch' : 'update'"
            :color="entryColor(idx)"
          >
            <template #title>
              <span class="version-title">
                <q-badge :color="entryColor(idx)" class="version-badge">{{ entry.version }}</q-badge>
                {{ entry.title }}
              </span>
            </template>
            <template #subtitle>
              <span class="version-date">
                <q-icon name="schedule" size="xs" class="q-mr-xs" />{{ formatDate(entry.date) }}, {{ entry.time }}
              </span>
            </template>
            <div class="feature-list">
              <div v-for="change in entry.changes" :key="change" class="feature-item">
                <q-icon name="check_circle" size="xs" :color="entryColor(idx)" class="feature-icon" />
                {{ change }}
              </div>
            </div>
          </q-timeline-entry>
        </q-timeline>

        <div v-if="!showAll && RELEASE_NOTES.length > INITIAL_COUNT" class="row justify-center q-mt-sm q-mb-xs">
          <q-btn flat color="primary" icon="expand_more" label="Mostrar versões anteriores" @click="showAll = true" />
        </div>
      </div>

      <!-- Tecnologias -->
      <div class="hd-card about-card">
        <div class="about-section-title">
          <span class="material-icons" style="font-size:20px;color:#3D52D5">build</span>
          Tecnologias utilizadas
        </div>
        <div class="about-tech-grid">
          <div v-for="t in techs" :key="t.name" class="about-tech-item">
            <span class="material-icons" :style="{ color: t.color, fontSize: '20px' }">{{ t.icon }}</span>
            <div>
              <div class="about-tech-name">{{ t.name }}</div>
              <div class="about-tech-desc">{{ t.desc }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Direitos de autor -->
      <div class="hd-card about-card">
        <div class="about-section-title">
          <span class="material-icons" style="font-size:20px;color:#3D52D5">gavel</span>
          Direitos de autor e propriedade intelectual
        </div>
        <p class="about-text" style="margin-bottom:12px">
          O <strong>Helpdesk Escolar</strong> é propriedade exclusiva de
          <strong>Pedro Sendas de Moura Pereira</strong>, docente do Grupo 550 — Informática
          do Agrupamento de Escolas Eça de Queirós.
        </p>
        <p class="about-text">
          A utilização, reprodução, distribuição, modificação ou qualquer outra forma de
          exploração deste software — no todo ou em parte — sem autorização escrita prévia
          do titular dos direitos de autor, é expressamente proibida.
        </p>
        <div class="about-copyright-box">
          <span class="material-icons" style="font-size:18px;color:#3D52D5;flex-shrink:0">copyright</span>
          <span>© 2026 Pedro Sendas de Moura Pereira — Todos os direitos reservados.</span>
        </div>
      </div>

      <!-- Rodapé -->
      <div class="about-footer">
        Helpdesk Escolar · maio de 2026 · desenvolvido com ❤ para o agrupamento
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { APP_VERSION, RELEASE_NOTES } from '../utils/version'

const INITIAL_COUNT = 8
const showAll = ref(false)

const visibleEntries = computed(() => showAll.value ? RELEASE_NOTES : RELEASE_NOTES.slice(0, INITIAL_COUNT))

const COLORS = ['teal-7', 'purple-7', 'blue-7', 'indigo-7', 'deep-purple-7', 'cyan-7', 'green-7', 'blue-grey-7']
function entryColor(idx: number) {
  return COLORS[idx % COLORS.length]
}

const MONTHS = ['janeiro','fevereiro','março','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro']
function formatDate(iso: string) {
  const [year, m, d] = iso.split('-')
  return `${parseInt(d)} de ${MONTHS[parseInt(m) - 1]} de ${year}`
}

const techs = [
  { name: 'FastAPI', desc: 'Backend Python — API REST assíncrona', icon: 'bolt', color: '#009688' },
  { name: 'SQLAlchemy + SQLite', desc: 'Base de dados — migrável para PostgreSQL', icon: 'storage', color: '#607D8B' },
  { name: 'Quasar / Vue 3', desc: 'Frontend SPA + PWA instalável', icon: 'web', color: '#1976D2' },
  { name: 'TypeScript + Pinia', desc: 'Estado da aplicação e tipagem', icon: 'code', color: '#3178C6' },
  { name: 'LDAP3 + MSAL', desc: 'Autenticação AD on-premise e Azure/Entra', icon: 'domain', color: '#0078D4' },
  { name: 'Web Push (RFC 8291)', desc: 'Notificações push nativas — iOS, Android, PC', icon: 'notifications', color: '#FF6B35' },
  { name: 'Docker + nginx', desc: 'Containerização e reverse proxy', icon: 'dns', color: '#2496ED' },
  { name: 'Jinja2 + fastapi-mail', desc: 'Templates HTML de email', icon: 'email', color: '#E91E63' },
]
</script>

<style scoped>
.about-page { padding: 0 0 40px; max-width: 100%; }

/* ── Hero ─────────────────────────────────────────────────── */
.hero {
  background: linear-gradient(135deg, #1a237e 0%, #283593 25%, #1565c0 60%, #0277bd 100%);
  padding: 52px 24px 44px;
  text-align: center;
  color: #fff;
}
.hero__icon-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 80px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 50%;
  margin-bottom: 18px;
  backdrop-filter: blur(4px);
}
.hero__title {
  font-size: 2rem;
  font-weight: 700;
  letter-spacing: -0.5px;
  margin-bottom: 10px;
}
.hero__badge {
  background: rgba(255, 255, 255, 0.25) !important;
  color: #fff !important;
  font-size: 0.85rem;
  font-weight: 600;
  letter-spacing: 0.5px;
  padding: 4px 12px;
  border-radius: 20px;
  margin-bottom: 14px;
}
.hero__subtitle {
  font-size: 0.95rem;
  opacity: 0.82;
  max-width: 480px;
  margin: 12px auto 0;
  line-height: 1.5;
}

/* ── Body ────────────────────────────────────────────────── */
.about-body {
  max-width: 760px;
  margin: 0 auto;
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.about-card { padding: 28px; border-radius: 14px; }

/* ── Author ──────────────────────────────────────────────── */
.about-author-row {
  display: flex;
  align-items: center;
  gap: 18px;
  margin-bottom: 20px;
}
.about-avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3D52D5, #6B7FE3);
  color: #fff;
  font-weight: 700;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.about-author-name { font-size: 18px; font-weight: 700; margin-bottom: 2px; }
.about-author-role { font-size: 13px; color: var(--c-muted); }
.about-text { font-size: 14px; line-height: 1.7; margin: 0; color: var(--c-text); }

/* ── Section title ───────────────────────────────────────── */
.about-section-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 16px;
  color: var(--c-text);
}

/* ── AI tools ────────────────────────────────────────────── */
.about-tools {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 24px;
}
.about-tool-card {
  border: 1px solid var(--c-border);
  border-radius: 10px;
  overflow: hidden;
}
.about-tool-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  color: #fff;
}
.about-tool-desc {
  font-size: 12px;
  line-height: 1.6;
  color: var(--c-muted);
  padding: 14px 16px;
  margin: 0;
}

/* ── Workflow ────────────────────────────────────────────── */
.about-workflow {
  border-top: 1px solid var(--c-border);
  padding-top: 20px;
  margin-top: 4px;
}
.about-workflow-title { font-size: 13px; font-weight: 600; margin-bottom: 10px; color: var(--c-text); }
.about-steps {
  margin: 0;
  padding-left: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.about-steps li { font-size: 13px; line-height: 1.6; color: var(--c-text); }
.about-quote {
  margin-top: 20px;
  padding: 16px 20px;
  border-left: 3px solid #3D52D5;
  background: var(--c-bg-alt, rgba(61,82,213,.06));
  border-radius: 0 8px 8px 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--c-muted);
  font-style: italic;
}

/* ── Timeline ────────────────────────────────────────────── */
.version-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1rem;
  font-weight: 600;
  flex-wrap: wrap;
}
.version-badge {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.3px;
  border-radius: 6px;
  padding: 2px 7px;
  flex-shrink: 0;
}
.version-date {
  font-size: 0.78rem;
  color: #9e9e9e;
  display: flex;
  align-items: center;
  margin-top: 2px;
}
.feature-list { display: flex; flex-direction: column; gap: 5px; margin-top: 6px; }
.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 0.82rem;
  line-height: 1.5;
  color: #555;
}
.feature-icon { margin-top: 2px; flex-shrink: 0; }
.body--dark .feature-item { color: #bbb; }

/* ── Tech grid ───────────────────────────────────────────── */
.about-tech-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}
.about-tech-item { display: flex; align-items: flex-start; gap: 10px; }
.about-tech-name { font-size: 13px; font-weight: 600; }
.about-tech-desc { font-size: 11px; color: var(--c-muted); }

/* ── Copyright ───────────────────────────────────────────── */
.about-copyright-box {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  padding: 12px 16px;
  background: var(--c-bg-alt, rgba(61,82,213,.06));
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--c-text);
}

/* ── Footer ──────────────────────────────────────────────── */
.about-footer {
  text-align: center;
  font-size: 12px;
  color: var(--c-muted);
  padding: 8px 0;
}

@media (max-width: 600px) {
  .about-tools { grid-template-columns: 1fr; }
  .about-tech-grid { grid-template-columns: 1fr; }
}
</style>
