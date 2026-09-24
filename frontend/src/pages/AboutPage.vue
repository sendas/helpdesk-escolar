<template>
  <div class="hd-page about-page">
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
          O Helpdesk Escolar foi concebido e é mantido por Pedro Sendas de Moura Pereira, professor de Informática
          do Agrupamento, desde maio de 2026. Nasceu da necessidade de reunir num só sistema todos os pedidos de apoio
          técnico — de docentes, não docentes, secretaria e direção — que antes se perdiam entre emails, mensagens e
          conversas de corredor, e de dar à equipa TIC uma forma clara de os acompanhar, priorizar e resolver.
        </p>
        <div class="about-stats">
          <div v-for="st in stats" :key="st.label" class="about-stat">
            <div class="about-stat-value">{{ st.value }}</div>
            <div class="about-stat-label">{{ st.label }}</div>
          </div>
        </div>
      </div>

      <!-- Método de criação -->
      <div class="hd-card about-card">
        <div class="about-section-title">
          <span class="material-icons" style="font-size:20px;color:#3D52D5">auto_awesome</span>
          Como foi construído — desenvolvimento com o Claude
        </div>

        <p class="about-text" style="margin-bottom:16px">
          A aplicação foi desenvolvida com <strong>programação assistida por inteligência artificial</strong>.
          O docente assume o papel de responsável pelo produto — decide o que é preciso, descreve cada pedido,
          avalia os resultados e aprova o que vai para produção — e o <strong>Claude</strong>, da Anthropic,
          faz o trabalho de engenharia.
        </p>

        <div class="about-claude">
          <div class="about-claude-head">
            <span class="about-claude-mark">✦</span>
            <div>
              <div style="font-weight:800;font-size:16px">Claude Code</div>
              <div style="font-size:12px;opacity:.8">Anthropic · modelos Claude Sonnet, Opus e Fable</div>
            </div>
          </div>
          <div class="about-claude-body">
            <p class="about-text" style="margin-bottom:12px">
              Praticamente todo o código da aplicação foi escrito pelo Claude Code, a trabalhar diretamente no
              repositório: lê o código existente, implementa as alterações no servidor e na interface, testa-as,
              atualiza a versão e as notas de atualização, e publica no GitHub. Mais de dois terços dos commits
              do projeto foram feitos pelo próprio Claude.
            </p>
            <div class="about-claude-sub">O que o Claude construiu, entre outras coisas</div>
            <ul class="about-claude-list">
              <li v-for="item in claudeWork" :key="item">{{ item }}</li>
            </ul>
          </div>
        </div>

        <p class="about-minor">
          <span class="material-icons" style="font-size:15px">info</span>
          O ChatGPT / Codex (OpenAI) foi usado pontualmente numa fase inicial, para algumas consultas de apoio.
        </p>

        <div class="about-workflow">
          <div class="about-workflow-title">Fluxo de trabalho</div>
          <ol class="about-steps">
            <li><strong>Pedido em linguagem natural</strong> — o docente descreve o que quer, em português, muitas vezes a partir do telemóvel e com uma captura de ecrã do problema (por exemplo: "os cartões do Painel não são clicáveis").</li>
            <li><strong>Análise do código</strong> — o Claude lê as partes relevantes da aplicação para perceber a causa ou o melhor sítio para a alteração, em vez de adivinhar.</li>
            <li><strong>Implementação</strong> — altera o servidor (FastAPI) e a interface (Vue/Quasar) em conjunto, incluindo migrações da base de dados quando necessário.</li>
            <li><strong>Teste real</strong> — arranca a aplicação com uma base de dados de teste, confirma o comportamento pela API e num browser automatizado, e tira capturas de ecrã.</li>
            <li><strong>Preview e ajustes</strong> — para mudanças visuais, envia as capturas antes de publicar; o docente pede afinações (cores, textos, disposição) até ficar como pretende.</li>
            <li><strong>Publicação</strong> — nova versão com notas em "Versão / Atualizações", commit e envio para o GitHub.</li>
            <li><strong>Instalação no servidor</strong> — no servidor da escola basta <code>git pull</code> e reconstruir os contentores Docker; a base de dados é preservada.</li>
          </ol>
        </div>

        <div class="about-quote">
          "A IA não substituiu o conhecimento do docente — multiplicou-o. Saber o que pedir, perceber se o resultado
          serve a escola e decidir o que vai para produção continuou a ser trabalho humano; o Claude tornou possível
          fazê-lo ao ritmo de várias melhorias por dia."
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
        Helpdesk Escolar · v{{ APP_VERSION }} · em desenvolvimento desde maio de 2026 · feito com ❤ para o agrupamento
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { APP_VERSION, RELEASE_NOTES } from '../utils/version'

const stats = [
  { value: `${RELEASE_NOTES.length}`, label: 'versões publicadas' },
  { value: '175+', label: 'commits no repositório' },
  { value: '~19 500', label: 'linhas de código' },
  { value: 'maio 2026', label: 'início do projeto' },
]

const claudeWork = [
  'Gestão completa de tickets: estados, prioridades, atribuição a técnicos e grupos, encaminhamento automático e tempos de resposta por categoria',
  'Login com a conta Microsoft (Entra ID), LDAP e contas locais, com importação de utilizadores e perfis automáticos',
  'Notificações por email e push no telemóvel, com agrupamento de várias atualizações num só email',
  'Leitura da caixa de correio: respostas por email entram no ticket e tickets fechados pela empresa de apoio fecham automaticamente',
  'Escalamento para a empresa de apoio informático e aviso/fecho automático de tickets inativos',
  'Painel inicial e login em design moderno (com opção de voltar ao clássico), modo escuro e versão para telemóvel (PWA)',
  'Estatísticas, base de conhecimento, sugestões, cópias de segurança automáticas (incluindo OneDrive) e registo de emails',
]

const techs = [
  { name: 'FastAPI', desc: 'Backend Python — API REST assíncrona', icon: 'bolt', color: '#009688' },
  { name: 'SQLAlchemy + SQLite', desc: 'Base de dados — migrável para PostgreSQL', icon: 'storage', color: '#607D8B' },
  { name: 'Quasar / Vue 3', desc: 'Frontend SPA + PWA instalável', icon: 'web', color: '#1976D2' },
  { name: 'TypeScript + Pinia', desc: 'Estado da aplicação e tipagem', icon: 'code', color: '#3178C6' },
  { name: 'LDAP3 + MSAL', desc: 'Autenticação AD on-premise e Azure/Entra', icon: 'domain', color: '#0078D4' },
  { name: 'Web Push (RFC 8291)', desc: 'Notificações push nativas — iOS, Android, PC', icon: 'notifications', color: '#FF6B35' },
  { name: 'Docker + nginx', desc: 'Containerização e reverse proxy', icon: 'dns', color: '#2496ED' },
  { name: 'Jinja2 + fastapi-mail', desc: 'Templates HTML de email', icon: 'email', color: '#E91E63' },
  { name: 'Microsoft Graph', desc: 'Leitura da caixa de correio e cópias no OneDrive', icon: 'cloud', color: '#0078D4' },
  { name: 'Chart.js', desc: 'Gráficos das estatísticas', icon: 'bar_chart', color: '#FF6384' },
]
</script>

<style scoped>
.about-page { padding: 0 0 40px; max-width: 100%; }

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

/* ── Stats ── */
.about-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 20px; }
.about-stat { padding: 12px; border-radius: 10px; background: var(--c-primary-soft); text-align: center; }
.about-stat-value { font-size: 18px; font-weight: 800; color: var(--c-primary); }
.about-stat-label { font-size: 11px; color: var(--c-muted); margin-top: 2px; }

/* ── Claude ── */
.about-claude { border: 1px solid var(--c-border); border-radius: 12px; overflow: hidden; margin-bottom: 14px; }
.about-claude-head {
  display: flex; align-items: center; gap: 12px; padding: 16px 18px; color: #fff;
  background: linear-gradient(135deg, #C15F3C, #D97757);
}
.about-claude-mark { font-size: 26px; line-height: 1; }
.about-claude-body { padding: 16px 18px; }
.about-claude-sub { font-size: 12px; font-weight: 700; color: var(--c-muted); text-transform: uppercase; letter-spacing: .04em; margin-bottom: 8px; }
.about-claude-list { margin: 0; padding-left: 18px; display: flex; flex-direction: column; gap: 6px; }
.about-claude-list li { font-size: 13px; line-height: 1.55; color: var(--c-text); }
.about-minor { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--c-muted); margin: 0 0 20px; }
.about-steps code { font-size: 12px; padding: 1px 5px; border-radius: 4px; background: var(--c-primary-soft); }

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
  .about-stats { grid-template-columns: repeat(2, 1fr); }
  .about-tech-grid { grid-template-columns: 1fr; }
}
</style>
