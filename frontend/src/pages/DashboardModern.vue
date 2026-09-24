<template>
  <div class="hd-page dash-page">
    <!-- Hero -->
    <section class="dash-hero">
      <div class="hero-blob hero-blob-1"></div>
      <div class="hero-blob hero-blob-2"></div>
      <div class="hero-content">
        <div class="hero-date">{{ todayLabel }}</div>
        <h1 class="hero-title">{{ greeting }}, {{ firstName }}</h1>
        <p class="hero-sub">{{ heroSubtitle }}</p>
        <div class="hero-actions">
          <router-link to="/tickets/new" class="hero-btn hero-btn-solid">
            <span class="material-icons">add</span> Novo pedido
          </router-link>
          <router-link to="/tickets" class="hero-btn hero-btn-glass">
            <span class="material-icons">inbox</span> Os meus tickets
          </router-link>
        </div>
      </div>
      <div class="hero-art" aria-hidden="true">
        <div class="hero-art-circle">
          <span class="material-icons">support_agent</span>
        </div>
        <div class="hero-chip hero-chip-1"><span class="material-icons">check_circle</span> Resolvido</div>
        <div class="hero-chip hero-chip-2"><span class="material-icons">bolt</span> Resposta rápida</div>
      </div>
    </section>

    <!-- Stat cards -->
    <div class="stat-grid" :class="auth.isStaff ? 'cols-5' : 'cols-3'">
      <component
        :is="s.to ? 'router-link' : 'div'"
        v-for="s in stats" :key="s.label"
        :to="s.to"
        class="stat-card" :class="[s.tone, { clickable: !!s.to }]"
      >
        <div class="stat-icon"><span class="material-icons">{{ s.icon }}</span></div>
        <div class="stat-value">{{ s.count }}</div>
        <div class="stat-label">{{ s.label }}</div>
        <div class="stat-sub">{{ s.sub }}</div>
        <span v-if="s.to" class="stat-go material-icons">arrow_forward</span>
      </component>
    </div>

    <div class="dash-body">
      <!-- Recent tickets -->
      <section class="hd-card recent-card">
        <div class="section-head">
          <div>
            <div class="section-title">Os meus tickets recentes</div>
            <div class="section-sub">Últimos pedidos submetidos</div>
          </div>
          <div class="section-actions">
            <CategoryFilterButton :categories="allCategories" @changed="load" />
            <router-link to="/tickets" class="section-link">
              Ver todos <span class="material-icons">arrow_forward</span>
            </router-link>
          </div>
        </div>

        <div class="recent-list">
          <div
            v-for="t in recent" :key="t.id"
            class="recent-row"
            :style="{ '--row-color': statusColor(t.status) }"
            @click="$router.push(`/tickets/${t.id}`)"
          >
            <div class="recent-dot"></div>
            <div class="recent-main">
              <div class="recent-title">{{ t.title }}</div>
              <div class="recent-meta">
                <span>T-{{ t.id }}</span>
                <span>·</span>
                <span>{{ t.category?.name || 'Sem categoria' }}</span>
                <span>·</span>
                <span>{{ timeAgo(t.updated_at) }}</span>
              </div>
            </div>
            <div class="recent-badges">
              <span class="status-pill">{{ statusLabel(t.status) }}</span>
              <PriorityBadge :priority="t.priority" />
            </div>
          </div>

          <div v-if="!recent.length" class="recent-empty">
            <div class="recent-empty-icon"><span class="material-icons">celebration</span></div>
            <div style="font-weight:600;margin-bottom:4px">Ainda não tem pedidos</div>
            <div style="font-size:13px;color:var(--c-muted);margin-bottom:14px">Quando precisar de ajuda, é só criar um novo pedido.</div>
            <router-link to="/tickets/new" class="hero-btn hero-btn-solid small">
              <span class="material-icons">add</span> Criar o primeiro pedido
            </router-link>
          </div>
        </div>
      </section>

      <!-- Quick categories -->
      <section class="hd-card quick-card">
        <div class="section-title">Novo pedido rápido</div>
        <div class="section-sub" style="margin-bottom:16px">Escolha a área do seu problema</div>
        <div class="quick-grid">
          <router-link
            v-for="cat in categories" :key="cat.id"
            :to="{ path: '/tickets/new', query: { categoria: cat.id } }"
            class="quick-tile"
            :style="{ '--tile-color': cat.color }"
          >
            <div class="quick-icon"><span class="material-icons">{{ cat.icon }}</span></div>
            <div class="quick-name">{{ cat.name }}</div>
            <div class="quick-sla">Resposta em {{ cat.sla_hours }}h</div>
          </router-link>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getTickets, getCategories } from '../api/tickets'
import { useAuthStore } from '../stores/auth'
import PriorityBadge from '../components/PriorityBadge.vue'
import CategoryFilterButton from '../components/CategoryFilterButton.vue'
import { timeAgo } from '../utils/dates'

const auth = useAuthStore()
const tickets = ref<any[]>([])
const allCategories = ref<any[]>([])

const hiddenIds = computed(() => auth.user?.hidden_category_ids ?? [])
const categories = computed(() => allCategories.value.filter(c => !hiddenIds.value.includes(c.id)).slice(0, 8))

async function load() {
  const [td] = await Promise.all([
    getTickets({ page: 1, size: 50, exclude_category_ids: hiddenIds.value }),
    loadSlaCounts(),
  ])
  tickets.value = td.items
}

onMounted(async () => {
  const [, cd] = await Promise.all([load(), getCategories()])
  allCategories.value = cd
})

const firstName = computed(() => auth.user?.display_name?.split(' ')[0] ?? '')

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return 'Bom dia'
  if (h < 20) return 'Boa tarde'
  return 'Boa noite'
})

const todayLabel = computed(() => {
  const s = new Date().toLocaleDateString('pt-PT', { weekday: 'long', day: 'numeric', month: 'long' })
  return s.charAt(0).toUpperCase() + s.slice(1)
})

const DONE = ['resolved', 'closed']
const IN_PROGRESS = ['assigned', 'in_progress', 'waiting_user']

const openCount = computed(() => tickets.value.filter(t => t.status === 'open').length)
const progressCount = computed(() => tickets.value.filter(t => IN_PROGRESS.includes(t.status)).length)
const doneCount = computed(() => tickets.value.filter(t => DONE.includes(t.status)).length)

const heroSubtitle = computed(() => {
  const active = openCount.value + progressCount.value
  if (!tickets.value.length) return 'Bem-vindo ao Centro de Apoio Digital. Precisa de ajuda com alguma coisa?'
  if (!active) return 'Não tem pedidos pendentes. Está tudo em ordem!'
  return `Tem ${active} pedido${active !== 1 ? 's' : ''} em acompanhamento. Precisa de ajuda com mais alguma coisa?`
})

const recent = computed(() => tickets.value.slice(0, 5))

const expiringCount = ref<number | null>(null)
const overdueCount = ref<number | null>(null)

async function loadSlaCounts() {
  if (!auth.isStaff) return
  const base = { page: 1, size: 1, exclude_category_ids: hiddenIds.value }
  const [exp, over] = await Promise.all([getTickets({ ...base, expiring: true }), getTickets({ ...base, overdue: true })])
  expiringCount.value = exp.total
  overdueCount.value = over.total
}

const stats = computed(() => {
  const list = [
    { label: 'Abertos', count: openCount.value, icon: 'inbox', sub: 'a aguardar resposta', tone: 'tone-blue', to: '/tickets?estado=abertos' },
    { label: 'Em curso', count: progressCount.value, icon: 'autorenew', sub: 'a ser tratados', tone: 'tone-violet', to: '/tickets?estado=em_curso' },
    { label: 'Resolvidos', count: doneCount.value, icon: 'task_alt', sub: 'resolvidos ou fechados', tone: 'tone-green', to: '/tickets?estado=resolvidos' },
  ]
  if (auth.isStaff) {
    list.push(
      { label: 'A expirar', count: expiringCount.value ?? '—', icon: 'hourglass_bottom', sub: 'prazo quase a terminar', tone: 'tone-amber', to: '/tickets?estado=a_expirar' },
      { label: 'Fora do prazo', count: overdueCount.value ?? '—', icon: 'alarm', sub: 'tempo de resposta ultrapassado', tone: 'tone-red', to: '/tickets?estado=fora_prazo' },
    )
  }
  return list
})

const STATUS_COLORS: Record<string, string> = {
  open: '#3B82F6', assigned: '#F59E0B', in_progress: '#8B5CF6', waiting_user: '#06B6D4', resolved: '#10B981', closed: '#94A3B8',
}

function statusColor(s: string) {
  return STATUS_COLORS[s] ?? '#94A3B8'
}

function statusLabel(s: string) {
  return { open: 'Aberto', assigned: 'Atribuído', in_progress: 'Em Curso', waiting_user: 'A aguardar', resolved: 'Resolvido', closed: 'Fechado' }[s] ?? s
}
</script>

<style scoped>
/* ── Hero ── */
.dash-hero {
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 28px 28px;
  margin-bottom: 20px;
  border-radius: 20px;
  color: #fff;
  background: linear-gradient(120deg, #1E3A8A 0%, #2563EB 50%, #0891B2 100%);
  box-shadow: 0 18px 40px rgba(37, 99, 235, .25);
}

.hero-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(2px);
  pointer-events: none;
}
.hero-blob-1 { width: 260px; height: 260px; right: -60px; top: -90px; background: rgba(255, 255, 255, .12); }
.hero-blob-2 { width: 180px; height: 180px; left: 38%; bottom: -110px; background: rgba(20, 184, 166, .35); }

.hero-content { position: relative; flex: 1; min-width: 0; }

.hero-date {
  display: inline-block;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: .02em;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, .18);
  margin-bottom: 12px;
}

.hero-title {
  font-size: 26px;
  font-weight: 700;
  line-height: 1.15;
  margin: 0 0 8px;
  color: #fff;
}

.hero-sub {
  font-size: 14px;
  line-height: 1.5;
  opacity: .9;
  margin: 0 0 18px;
  max-width: 520px;
}

.hero-actions { display: flex; gap: 10px; flex-wrap: wrap; }

.hero-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 700;
  text-decoration: none;
  transition: transform .15s ease, box-shadow .15s ease, background .15s ease;
}
.hero-btn .material-icons { font-size: 18px; }
.hero-btn:hover { transform: translateY(-2px); }
.hero-btn.small { padding: 8px 14px; font-size: 13px; }

.hero-btn-solid {
  background: #fff;
  color: #4338CA;
  box-shadow: 0 8px 18px rgba(15, 23, 42, .18);
}
.recent-empty .hero-btn-solid {
  background: linear-gradient(135deg, var(--c-primary), var(--c-primary-strong));
  color: #fff;
}
.hero-btn-glass {
  background: rgba(255, 255, 255, .16);
  border: 1px solid rgba(255, 255, 255, .35);
  color: #fff;
}
.hero-btn-glass:hover { background: rgba(255, 255, 255, .26); }

.hero-art {
  position: relative;
  width: 200px;
  height: 150px;
  flex-shrink: 0;
  display: none;
}
.hero-art-circle {
  position: absolute;
  inset: 10px 30px;
  border-radius: 50%;
  background: rgba(255, 255, 255, .16);
  border: 1px solid rgba(255, 255, 255, .3);
  display: grid;
  place-items: center;
}
.hero-art-circle .material-icons { font-size: 64px; color: #fff; }

.hero-chip {
  position: absolute;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 10px;
  border-radius: 10px;
  background: #fff;
  color: #1E293B;
  font-size: 11.5px;
  font-weight: 700;
  box-shadow: 0 10px 22px rgba(15, 23, 42, .2);
  white-space: nowrap;
}
.hero-chip .material-icons { font-size: 15px; }
.hero-chip-1 { top: 4px; left: -6px; }
.hero-chip-1 .material-icons { color: #10B981; }
.hero-chip-2 { bottom: 4px; right: -8px; }
.hero-chip-2 .material-icons { color: #F59E0B; }

/* ── Stats ── */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.stat-card {
  position: relative;
  overflow: hidden;
  border-radius: 16px;
  padding: 16px;
  color: #fff;
  box-shadow: 0 10px 24px var(--tone-shadow);
  transition: transform .15s ease;
}
.stat-card { display: block; text-decoration: none; }
.stat-card.clickable { cursor: pointer; }
.stat-card.clickable:hover { transform: translateY(-3px); box-shadow: 0 14px 30px var(--tone-shadow); }
.stat-go {
  position: absolute; right: 14px; top: 16px; z-index: 1;
  font-size: 18px; opacity: .75; transition: transform .15s ease, opacity .15s ease;
}
.stat-card.clickable:hover .stat-go { transform: translateX(3px); opacity: 1; }
.stat-card::after {
  content: '';
  position: absolute;
  width: 120px;
  height: 120px;
  right: -40px;
  bottom: -50px;
  border-radius: 50%;
  background: rgba(255, 255, 255, .14);
}

.tone-blue   { background: linear-gradient(135deg, #0EA5E9, #2563EB); --tone-shadow: rgba(14, 165, 233, .28); }
.tone-amber  { background: linear-gradient(135deg, #F59E0B, #F97316); --tone-shadow: rgba(245, 158, 11, .28); }
.tone-green  { background: linear-gradient(135deg, #10B981, #14B8A6); --tone-shadow: rgba(16, 185, 129, .28); }
.tone-red    { background: linear-gradient(135deg, #EF4444, #DC2626); --tone-shadow: rgba(239, 68, 68, .28); }
.tone-violet { background: linear-gradient(135deg, #4F46E5, #6366F1); --tone-shadow: rgba(79, 70, 229, .28); }

.stat-icon {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: rgba(255, 255, 255, .22);
  display: grid;
  place-items: center;
  margin-bottom: 14px;
}
.stat-icon .material-icons { font-size: 20px; color: #fff; }

.stat-value { font-size: 30px; font-weight: 800; line-height: 1; margin-bottom: 6px; }
.stat-label { font-size: 13px; font-weight: 700; }
.stat-sub { font-size: 11.5px; opacity: .85; margin-top: 2px; }

/* ── Body ── */
.dash-body { display: flex; flex-direction: column; gap: 16px; }

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 18px 20px 14px;
}
.section-title { font-size: 15px; font-weight: 700; color: var(--c-text); }
.section-sub { font-size: 12px; color: var(--c-muted); margin-top: 2px; }
.section-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 600;
  color: var(--c-primary);
  text-decoration: none;
  white-space: nowrap;
  padding: 6px 10px;
  border-radius: 8px;
  background: var(--c-primary-soft, rgba(64, 87, 216, .1));
}
.section-link .material-icons { font-size: 16px; }
.section-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }

/* Recent list */
.recent-card { overflow: hidden; }
.recent-list { display: flex; flex-direction: column; padding: 0 12px 12px; gap: 8px; }

.recent-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid var(--c-border);
  border-left: 4px solid var(--row-color);
  background: var(--c-surface);
  cursor: pointer;
  transition: transform .12s ease, box-shadow .12s ease, background .12s ease;
}
.recent-row:hover {
  transform: translateX(2px);
  box-shadow: 0 6px 16px rgba(15, 23, 42, .08);
  background: color-mix(in srgb, var(--row-color) 6%, var(--c-surface));
}

.recent-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--row-color);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--row-color) 20%, transparent);
}

.recent-main { flex: 1; min-width: 0; }
.recent-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.recent-meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  font-size: 11.5px;
  color: var(--c-muted);
  margin-top: 3px;
}

.recent-badges { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.status-pill {
  font-size: 11.5px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 999px;
  color: var(--row-color);
  background: color-mix(in srgb, var(--row-color) 14%, transparent);
  white-space: nowrap;
}

.recent-empty { text-align: center; padding: 28px 16px; }
.recent-empty-icon {
  width: 52px;
  height: 52px;
  margin: 0 auto 12px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #F59E0B, #F97316);
}
.recent-empty-icon .material-icons { color: #fff; font-size: 26px; }

/* Quick categories */
.quick-card { padding: 18px 20px 20px; }
.quick-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}
.quick-tile {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 14px;
  border-radius: 14px;
  text-decoration: none;
  background: color-mix(in srgb, var(--tile-color) 10%, var(--c-surface));
  border: 1px solid color-mix(in srgb, var(--tile-color) 22%, transparent);
  transition: transform .15s ease, box-shadow .15s ease;
}
.quick-tile:hover {
  transform: translateY(-3px);
  box-shadow: 0 10px 20px color-mix(in srgb, var(--tile-color) 25%, transparent);
}
.quick-icon {
  width: 36px;
  height: 36px;
  border-radius: 11px;
  display: grid;
  place-items: center;
  margin-bottom: 8px;
  background: var(--tile-color);
  box-shadow: 0 6px 14px color-mix(in srgb, var(--tile-color) 35%, transparent);
}
.quick-icon .material-icons { font-size: 19px; color: #fff; }
.quick-name { font-size: 13px; font-weight: 700; color: var(--c-text); line-height: 1.25; }
.quick-sla { font-size: 11px; color: var(--c-muted); }

/* ── Responsive ── */
@media (max-width: 560px) {
  .dash-hero { padding: 22px 18px; border-radius: 16px; }
  .hero-title { font-size: 22px; }
  .recent-badges .status-pill { display: none; }
}

@media (min-width: 820px) {
  .hero-art { display: block; }
  .hero-title { font-size: 30px; }
}

@media (min-width: 1100px) {
  .stat-grid { grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }
}

@media (min-width: 1300px) {
  .stat-grid.cols-5 { grid-template-columns: repeat(5, 1fr); }
  .stat-grid.cols-5 .stat-value { font-size: 26px; }
}

@media (min-width: 1300px) {
  .dash-body { flex-direction: row; align-items: flex-start; gap: 20px; }
  .recent-card { flex: 1; min-width: 0; }
  .quick-card { width: 360px; flex-shrink: 0; }
}
</style>
