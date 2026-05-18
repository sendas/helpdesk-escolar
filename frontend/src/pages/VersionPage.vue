<template>
  <div class="hd-page version-page">
    <!-- Hero -->
    <div class="hero">
      <div class="hero__icon-wrap">
        <q-icon name="new_releases" size="40px" color="white" />
      </div>
      <div class="hero__label">Versão atual</div>
      <div class="hero__version">v{{ APP_VERSION }}</div>
      <div class="hero__date">
        <q-icon name="schedule" size="xs" class="q-mr-xs" style="opacity:.75" />
        {{ formatDate(APP_VERSION_DATE) }}, {{ APP_VERSION_TIME }}
      </div>
    </div>

    <!-- Timeline -->
    <div class="q-pa-md">
      <div class="row justify-center">
        <div style="max-width: 780px; width: 100%">

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

        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { APP_VERSION, APP_VERSION_DATE, APP_VERSION_TIME, RELEASE_NOTES } from '../utils/version'

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
</script>

<style scoped>
.version-page { padding: 0 0 40px; max-width: 100%; }

/* ── Hero ─────────────────────────────────────────────────── */
.hero {
  background: linear-gradient(135deg, #1a237e 0%, #283593 25%, #1565c0 60%, #0277bd 100%);
  padding: 44px 24px 36px;
  text-align: center;
  color: #fff;
}
.hero__icon-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 70px;
  height: 70px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 50%;
  margin-bottom: 14px;
  backdrop-filter: blur(4px);
}
.hero__label {
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  opacity: 0.72;
  margin-bottom: 6px;
}
.hero__version {
  font-size: 2.4rem;
  font-weight: 700;
  letter-spacing: -1px;
  line-height: 1;
  margin-bottom: 10px;
}
.hero__date {
  display: inline-flex;
  align-items: center;
  font-size: 0.88rem;
  opacity: 0.78;
}

/* ── Section label ───────────────────────────────────────── */
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

/* ── Timeline entries ────────────────────────────────────── */
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
</style>
