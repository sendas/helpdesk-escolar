<template>
  <div class="hd-page version-page">
    <!-- Version info strip -->
    <div class="version-strip">
      <div class="version-strip__badge">v{{ APP_VERSION }}</div>
      <div class="version-strip__date">
        <span class="material-icons" style="font-size:14px;opacity:.7">schedule</span>
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

/* ── Version strip ───────────────────────────────────────── */
.version-strip {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 24px;
  background: var(--c-surface);
  border-bottom: 1px solid var(--c-border);
  flex-wrap: wrap;
}
.version-strip__badge {
  background: var(--c-primary);
  color: #fff;
  font-size: 0.82rem;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 20px;
  letter-spacing: 0.3px;
}
.version-strip__date {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 0.82rem;
  color: var(--c-muted);
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
