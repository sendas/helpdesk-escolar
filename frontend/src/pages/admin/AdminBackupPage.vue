<template>
  <div class="hd-page backup-page">
    <div class="page-heading">
      <div>
        <h1>Backup &amp; Restauro</h1>
        <p>Cópias de segurança manuais e automáticas dos dados do helpdesk.</p>
      </div>
      <button class="hd-btn hd-btn-primary" :disabled="backing" @click="doServerBackup">
        <span class="material-icons">{{ backing ? 'hourglass_empty' : 'save' }}</span>
        {{ backing ? 'A criar...' : 'Criar cópia agora' }}
      </button>
    </div>

    <div class="backup-grid">
      <section class="hd-card backup-card">
        <div class="card-title">
          <span class="material-icons">settings_backup_restore</span>
          Backup automático
        </div>
        <p class="card-copy">Define se o servidor deve criar cópias periódicas e onde as deve guardar.</p>

        <label class="backup-toggle">
          <input type="checkbox" v-model="config.enabled" />
          <span>Ativar cópias automáticas</span>
        </label>

        <div class="form-grid">
          <label>
            Frequência
            <select class="hd-select" v-model.number="config.interval_hours">
              <option :value="1">De hora a hora</option>
              <option :value="6">A cada 6 horas</option>
              <option :value="12">A cada 12 horas</option>
              <option :value="24">Diariamente</option>
              <option :value="168">Semanalmente</option>
            </select>
          </label>
          <label>
            Manter últimas
            <input class="hd-input" type="number" min="1" max="365" v-model.number="config.retention" />
          </label>
          <label class="span-2">
            Destino principal
            <input class="hd-input" v-model="config.directory" placeholder="/app/data/backups" />
          </label>
          <label class="span-2">
            Destino secundário <span class="optional-tag">opcional</span>
            <input class="hd-input" v-model="config.secondary_directory" placeholder="ex: /mnt/nas/backups ou \\\\servidor\\pasta" />
            <span class="field-hint">Partilha de rede montada, disco externo ou outro caminho acessível pelo servidor. Deixar vazio para não usar.</span>
          </label>
        </div>

        <button class="hd-btn hd-btn-outline" :disabled="saving" @click="saveConfig">
          <span class="material-icons">check</span>
          {{ saving ? 'A guardar...' : 'Guardar configuração' }}
        </button>
        <div v-if="message" class="status-line" :class="{ error: messageError }">{{ message }}</div>
      </section>

      <section class="hd-card backup-card">
        <div class="card-title">
          <span class="material-icons">download</span>
          Exportar ficheiro
        </div>
        <p class="card-copy">Descarrega uma cópia JSON para guardar fora do servidor.</p>
        <div class="stats-row">
          <div><strong>{{ stats.tickets }}</strong><span>Tickets</span></div>
          <div><strong>{{ stats.users }}</strong><span>Utilizadores</span></div>
          <div><strong>{{ stats.categories }}</strong><span>Categorias</span></div>
        </div>
        <button class="hd-btn hd-btn-outline full" :disabled="downloading" @click="doDownloadBackup">
          <span class="material-icons">{{ downloading ? 'hourglass_empty' : 'file_download' }}</span>
          {{ downloading ? 'A exportar...' : 'Descarregar backup' }}
        </button>
      </section>
    </div>

    <section class="hd-card backup-card">
      <div class="card-title">
        <span class="material-icons">cloud_upload</span>
        Importar / Restaurar
      </div>
      <p class="card-copy">Faz sempre uma cópia antes de restaurar.</p>

      <div
        class="hd-dropzone"
        @click="fileInput?.click()"
        @dragover.prevent
        @drop.prevent="onDrop"
      >
        <span class="material-icons">{{ restoreFile ? 'description' : 'upload_file' }}</span>
        <div>{{ restoreFile ? restoreFile.name : 'Arrastar ficheiro JSON ou clicar para selecionar' }}</div>
        <small>Apenas ficheiros .json</small>
        <input ref="fileInput" type="file" accept=".json" style="display:none" @change="onFileChange" />
      </div>
      <div v-if="restoreFile" class="warning-line">Restauro ainda não está ativo nesta versão. O ficheiro foi selecionado, mas nada será substituído.</div>
    </section>

    <section class="hd-card backup-card">
      <div class="card-title">
        <span class="material-icons">history</span>
        Registo de cópias
        <button class="hd-icon-btn refresh-btn" title="Atualizar" @click="loadHistory">
          <span class="material-icons" style="font-size:18px">refresh</span>
        </button>
      </div>
      <div v-if="loadingHistory" class="empty-log">A carregar…</div>
      <div v-else class="log-list">
        <div v-for="entry in history" :key="entry.id" class="log-item">
          <span class="material-icons" :class="{ ok: entry.ok, warn: !entry.ok && entry.secondary_error }">
            {{ entry.ok ? 'check_circle' : entry.secondary_error ? 'warning' : 'error' }}
          </span>
          <div>
            <strong>{{ entry.filename }}</strong>
            <span class="log-badge" :class="entry.source">{{ entry.source === 'auto' ? 'automático' : 'manual' }}</span>
            <small class="log-date">{{ formatDate(entry.date) }}</small>
            <div class="log-locations">
              <span v-for="loc in entry.locations" :key="loc" class="log-loc">
                <span class="material-icons" style="font-size:13px;vertical-align:middle">folder</span> {{ loc }}
              </span>
            </div>
            <div v-if="entry.secondary_error" class="log-sec-error">
              <span class="material-icons" style="font-size:13px;vertical-align:middle">warning</span>
              Destino secundário: {{ entry.secondary_error }}
            </div>
          </div>
        </div>
        <div v-if="!history.length" class="empty-log">Ainda não há cópias de segurança registadas.</div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { downloadBackup, getAdminStats, getBackupConfig, getBackupHistory, runServerBackup, updateBackupConfig } from '../../api/tickets'
import type { BackupHistoryEntry } from '../../api/tickets'

const backing = ref(false)
const downloading = ref(false)
const saving = ref(false)
const loadingHistory = ref(false)
const message = ref('')
const messageError = ref(false)
const restoreFile = ref<File | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const stats = ref({ tickets: '—', users: '—', categories: '—' })
const config = ref({ enabled: false, interval_hours: 24, directory: '/app/data/backups', retention: 14, secondary_directory: '' })
const history = ref<BackupHistoryEntry[]>([])

onMounted(async () => {
  try {
    const [s, cfg] = await Promise.all([getAdminStats(), getBackupConfig()])
    stats.value = { tickets: s.total ?? '—', users: s.user_count ?? '—', categories: s.category_count ?? '—' }
    config.value = {
      enabled: !!cfg.enabled,
      interval_hours: Number(cfg.interval_hours || 24),
      directory: cfg.directory || '/app/data/backups',
      retention: Number(cfg.retention || 14),
      secondary_directory: cfg.secondary_directory || '',
    }
  } catch {
    showMessage('Não foi possível carregar a configuração de backup.', true)
  }
  await loadHistory()
})

async function loadHistory() {
  loadingHistory.value = true
  try {
    history.value = await getBackupHistory()
  } catch {
    history.value = []
  } finally {
    loadingHistory.value = false
  }
}

async function saveConfig() {
  saving.value = true
  message.value = ''
  try {
    config.value = await updateBackupConfig(config.value)
    showMessage('Configuração guardada.', false)
  } catch {
    showMessage('Erro ao guardar configuração.', true)
  } finally {
    saving.value = false
  }
}

async function doServerBackup() {
  backing.value = true
  try {
    const result = await runServerBackup()
    if (result.secondary_error) {
      showMessage(`Cópia criada em ${result.path}. Aviso no destino secundário: ${result.secondary_error}`, true)
    } else {
      showMessage(`Cópia criada com sucesso${result.locations.length > 1 ? ' em ' + result.locations.length + ' destinos' : ''}.`, false)
    }
    await loadHistory()
  } catch {
    showMessage('Erro ao criar cópia de segurança.', true)
  } finally {
    backing.value = false
  }
}

async function doDownloadBackup() {
  downloading.value = true
  try {
    await downloadBackup()
  } catch {
    showMessage('Erro ao descarregar backup.', true)
  } finally {
    downloading.value = false
  }
}

function showMessage(text: string, isError: boolean) {
  message.value = text
  messageError.value = isError
  setTimeout(() => { if (message.value === text) message.value = '' }, 6000)
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  restoreFile.value = input.files?.[0] ?? null
}

function onDrop(e: DragEvent) {
  const file = e.dataTransfer?.files?.[0]
  if (file?.name.endsWith('.json')) restoreFile.value = file
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleString('pt-PT', { dateStyle: 'short', timeStyle: 'short' })
  } catch { return iso }
}
</script>

<style scoped>
.backup-page { max-width: 1180px; }
.page-heading {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}
.page-heading h1 { font-size: 24px; margin: 0 0 6px; }
.page-heading p, .card-copy { color: var(--c-muted); margin: 0; font-size: 14px; }
.backup-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(300px, .7fr);
  gap: 18px;
  margin-bottom: 18px;
}
.backup-card { padding: 22px; margin-bottom: 18px; }
.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  margin-bottom: 6px;
}
.card-title .material-icons { color: var(--c-primary); }
.refresh-btn { margin-left: auto; }
.backup-toggle {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 18px 0;
  font-weight: 600;
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr 160px;
  gap: 14px;
  margin-bottom: 16px;
}
.form-grid label {
  display: grid;
  gap: 6px;
  color: var(--c-muted);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}
.span-2 { grid-column: 1 / -1; }
.optional-tag {
  font-size: 10px;
  font-weight: 400;
  text-transform: none;
  background: var(--c-border);
  border-radius: 4px;
  padding: 1px 6px;
  margin-left: 6px;
  vertical-align: middle;
}
.field-hint {
  font-size: 11px;
  font-weight: 400;
  text-transform: none;
  color: var(--c-muted);
  margin-top: 2px;
}
.status-line, .warning-line {
  margin-top: 12px;
  color: var(--c-muted);
  font-size: 13px;
}
.status-line.error { color: #dc2626; }
.warning-line { color: #92400e; }
.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin: 20px 0;
}
.stats-row div {
  border: 1px solid var(--c-border);
  border-radius: 8px;
  padding: 12px;
  text-align: center;
}
.stats-row strong { display: block; font-size: 22px; color: var(--c-primary); }
.stats-row span { font-size: 11px; color: var(--c-muted); }
.full { width: 100%; justify-content: center; }
.hd-dropzone { cursor: pointer; }
.hd-dropzone .material-icons {
  display: block;
  font-size: 34px;
  color: var(--c-muted);
  margin-bottom: 8px;
}
.hd-dropzone small { display: block; margin-top: 4px; color: var(--c-muted); }
.log-list { display: grid; gap: 10px; }
.log-item {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 10px;
  align-items: start;
  padding: 12px;
  border: 1px solid var(--c-border);
  border-radius: 8px;
}
.log-item .material-icons { color: #ef4444; }
.log-item .material-icons.ok { color: #22c55e; }
.log-item .material-icons.warn { color: #f59e0b; }
.log-item strong { display: inline; margin-right: 8px; }
.log-badge {
  font-size: 10px;
  border-radius: 4px;
  padding: 2px 6px;
  font-weight: 600;
  text-transform: uppercase;
  vertical-align: middle;
}
.log-badge.manual { background: #dbeafe; color: #1e40af; }
.log-badge.auto { background: #dcfce7; color: #166534; }
.log-date { display: block; color: var(--c-muted); margin-top: 3px; }
.log-locations { margin-top: 4px; display: flex; flex-direction: column; gap: 2px; }
.log-loc { font-size: 11px; color: var(--c-muted); }
.log-sec-error { font-size: 11px; color: #dc2626; margin-top: 4px; }
.empty-log { color: var(--c-muted); font-size: 13px; }
@media (max-width: 820px) {
  .page-heading, .backup-grid { display: grid; grid-template-columns: 1fr; }
  .page-heading .hd-btn { width: 100%; justify-content: center; }
  .backup-card { padding: 18px; }
  .form-grid { grid-template-columns: 1fr; }
  .stats-row { grid-template-columns: 1fr; }
}
</style>
