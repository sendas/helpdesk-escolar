<template>
  <div class="hd-page about-page">
    <!-- Hero banner -->
    <div class="hero">
      <div class="hero__icon-wrap">
        <q-icon name="support_agent" size="48px" color="white" />
      </div>
      <div class="hero__title">Helpdesk</div>
      <q-badge class="hero__badge">v{{ APP_VERSION }}</q-badge>
      <div class="hero__subtitle">
        Sistema de gestão de pedidos de suporte e assistência técnica
      </div>
    </div>

    <!-- Page body -->
    <div class="q-pa-md">
      <div class="row justify-center">
        <div style="max-width: 780px; width: 100%">

          <!-- Version history -->
          <div class="section-label">
            <q-icon name="tag" size="xs" class="q-mr-xs" />Historial de versões
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

          <div v-if="!showAll && RELEASE_NOTES.length > INITIAL_COUNT" class="row justify-center q-mb-lg">
            <q-btn flat color="primary" icon="expand_more" label="Mostrar versões anteriores" @click="showAll = true" />
          </div>

          <!-- Tech stack -->
          <div class="section-label">
            <q-icon name="build" size="xs" class="q-mr-xs" />Tecnologias utilizadas
          </div>
          <div class="row q-col-gutter-sm q-mb-lg">
            <div v-for="tech in techs" :key="tech.name" class="col-6 col-sm-4 col-md-3">
              <q-card flat bordered class="tech-card">
                <q-card-section class="q-pa-sm row items-center no-wrap q-gutter-sm">
                  <q-icon :name="tech.icon" :color="tech.color" size="26px" />
                  <div>
                    <div class="text-weight-bold text-body2">{{ tech.name }}</div>
                    <div class="text-caption text-grey-6">{{ tech.desc }}</div>
                  </div>
                </q-card-section>
              </q-card>
            </div>
          </div>

        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { APP_VERSION, RELEASE_NOTES } from '../utils/version'

const INITIAL_COUNT = 10
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
  { name: 'FastAPI',     desc: 'API REST',        icon: 'bolt',                     color: 'teal-6' },
  { name: 'SQLite',      desc: 'Base de dados',   icon: 'storage',                  color: 'brown-6' },
  { name: 'Vue 3',       desc: 'Frontend',        icon: 'code',                     color: 'teal-5' },
  { name: 'Quasar',      desc: 'UI Framework',    icon: 'palette',                  color: 'blue-6' },
  { name: 'Docker',      desc: 'Containerização', icon: 'inventory_2',              color: 'blue-8' },
  { name: 'TypeScript',  desc: 'Tipagem',         icon: 'integration_instructions', color: 'indigo-6' },
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

/* ── Section labels ──────────────────────────────────────── */
.section-label {
  display: flex;
  align-items: center;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  color: #9e9e9e;
  margin-top: 28px;
  margin-bottom: 14px;
}

/* ── Version timeline ────────────────────────────────────── */
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
.feature-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-top: 6px;
}
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

/* ── Tech cards ──────────────────────────────────────────── */
.tech-card {
  transition: transform 0.15s ease, box-shadow 0.15s ease;
  border-radius: 8px !important;
}
.tech-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1) !important;
}
</style>
