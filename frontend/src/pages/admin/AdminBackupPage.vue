<template>
  <div class="hd-page">
    <h1 style="font-size:22px;margin-bottom:24px">Backup &amp; Restauro</h1>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;align-items:start;margin-bottom:20px">
      <!-- Backup card -->
      <div class="hd-card" style="padding:28px">
        <div class="hd-row" style="margin-bottom:4px">
          <span class="material-icons" style="color:#3D52D5;margin-right:8px">cloud_download</span>
          <div style="font-weight:600;font-size:15px">Exportar dados</div>
        </div>
        <div style="font-size:13px;color:var(--c-muted);margin-bottom:20px">
          Exporta todos os tickets, comentários, utilizadores e categorias para um ficheiro JSON.
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:20px">
          <div style="text-align:center;border:1px solid var(--c-border);border-radius:8px;padding:12px">
            <div style="font-size:22px;font-weight:700;color:var(--c-primary)">{{ stats.tickets }}</div>
            <div style="font-size:11px;color:var(--c-muted)">Tickets</div>
          </div>
          <div style="text-align:center;border:1px solid var(--c-border);border-radius:8px;padding:12px">
            <div style="font-size:22px;font-weight:700;color:var(--c-primary)">{{ stats.users }}</div>
            <div style="font-size:11px;color:var(--c-muted)">Utilizadores</div>
          </div>
          <div style="text-align:center;border:1px solid var(--c-border);border-radius:8px;padding:12px">
            <div style="font-size:22px;font-weight:700;color:var(--c-primary)">{{ stats.categories }}</div>
            <div style="font-size:11px;color:var(--c-muted)">Categorias</div>
          </div>
        </div>

        <button class="hd-btn hd-btn-primary" style="width:100%" :disabled="backing" @click="doBackup">
          <span class="material-icons" style="font-size:16px">{{ backing ? 'hourglass_empty' : 'download' }}</span>
          {{ backing ? 'A exportar...' : 'Fazer backup agora' }}
        </button>
        <div v-if="lastBackup" style="font-size:12px;color:var(--c-muted);text-align:center;margin-top:8px">
          Último backup: {{ lastBackup }}
        </div>
      </div>

      <!-- Restore card -->
      <div class="hd-card" style="padding:28px">
        <div class="hd-row" style="margin-bottom:4px">
          <span class="material-icons" style="color:#F59E0B;margin-right:8px">cloud_upload</span>
          <div style="font-weight:600;font-size:15px">Importar / Restaurar</div>
        </div>
        <div style="font-size:13px;color:var(--c-muted);margin-bottom:20px">
          Restaura dados a partir de um ficheiro JSON exportado anteriormente. Operação irreversível.
        </div>

        <div
          class="hd-dropzone"
          style="margin-bottom:20px;cursor:pointer"
          @click="fileInput?.click()"
          @dragover.prevent
          @drop.prevent="onDrop"
        >
          <span class="material-icons" style="font-size:32px;color:var(--c-muted);margin-bottom:8px;display:block">
            {{ restoreFile ? 'description' : 'upload_file' }}
          </span>
          <div style="font-size:13.5px;color:var(--c-muted)">
            {{ restoreFile ? restoreFile.name : 'Arrastar ficheiro JSON ou clicar para selecionar' }}
          </div>
          <div style="font-size:12px;color:var(--c-muted);margin-top:4px">Apenas ficheiros .json</div>
          <input ref="fileInput" type="file" accept=".json" style="display:none" @change="onFileChange" />
        </div>

        <div v-if="restoreFile" style="border:1px solid #F59E0B33;background:#FFF9EB;border-radius:8px;padding:12px;margin-bottom:16px;font-size:13px;color:#92400E">
          <span class="material-icons" style="font-size:14px;vertical-align:middle;margin-right:4px">warning</span>
          Esta operação substituirá os dados existentes. Faça um backup antes de continuar.
        </div>

        <button
          class="hd-btn"
          style="width:100%;background:#F59E0B;color:#fff;justify-content:center"
          :disabled="!restoreFile || restoring"
          @click="doRestore"
        >
          <span class="material-icons" style="font-size:16px">restore</span>
          {{ restoring ? 'A restaurar...' : 'Restaurar dados' }}
        </button>
      </div>
    </div>

    <!-- Operation log -->
    <div class="hd-card" style="padding:20px">
      <div style="font-weight:600;font-size:14px;margin-bottom:4px">Registo de operações</div>
      <div style="font-size:12px;color:var(--c-muted);margin-bottom:16px">Histórico de backups e restauros</div>
      <table class="hd-table">
        <thead><tr><th>DATA</th><th>OPERAÇÃO</th><th>UTILIZADOR</th><th>ESTADO</th><th>DETALHES</th></tr></thead>
        <tbody>
          <tr v-for="entry in log" :key="entry.id">
            <td style="color:var(--c-muted);white-space:nowrap">{{ entry.date }}</td>
            <td style="font-weight:500">{{ entry.op }}</td>
            <td>
              <div class="hd-row" style="gap:6px">
                <AvatarCircle :name="entry.user" size="22" />
                <span style="font-size:13px">{{ entry.user }}</span>
              </div>
            </td>
            <td>
              <span :style="entry.ok ? 'color:#22C55E;font-size:12px' : 'color:#EF4444;font-size:12px'">
                <span class="material-icons" style="font-size:13px;vertical-align:middle">{{ entry.ok ? 'check_circle' : 'error' }}</span>
                {{ entry.ok ? 'Sucesso' : 'Erro' }}
              </span>
            </td>
            <td style="font-size:12px;color:var(--c-muted)">{{ entry.detail }}</td>
          </tr>
          <tr v-if="!log.length">
            <td colspan="5" style="text-align:center;color:var(--c-muted);padding:32px">Sem registos.</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getAdminStats, downloadBackup } from '../../api/tickets'
import AvatarCircle from '../../components/AvatarCircle.vue'

const backing = ref(false)
const restoring = ref(false)
const restoreFile = ref<File | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const lastBackup = ref('')

const stats = ref({ tickets: '—', users: '—', categories: '—' })
const log = ref<any[]>([])

onMounted(async () => {
  try {
    const s = await getAdminStats()
    stats.value = {
      tickets: s.total ?? '—',
      users: s.user_count ?? '—',
      categories: s.category_count ?? '—',
    }
  } catch { /* ignore */ }
})

async function doBackup() {
  backing.value = true
  try {
    await downloadBackup()
    lastBackup.value = new Date().toLocaleString('pt-PT')
    log.value.unshift({
      id: Date.now(), date: lastBackup.value, op: 'Exportar backup',
      user: 'Admin', ok: true, detail: 'helpdesk-backup.json',
    })
  } catch {
    log.value.unshift({
      id: Date.now(), date: new Date().toLocaleString('pt-PT'), op: 'Exportar backup',
      user: 'Admin', ok: false, detail: 'Erro ao exportar',
    })
  } finally { backing.value = false }
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  restoreFile.value = input.files?.[0] ?? null
}

function onDrop(e: DragEvent) {
  const file = e.dataTransfer?.files?.[0]
  if (file?.name.endsWith('.json')) restoreFile.value = file
}

async function doRestore() {
  if (!restoreFile.value || !confirm('Restaurar dados? Esta operação é irreversível.')) return
  restoring.value = true
  await new Promise(r => setTimeout(r, 1500))
  log.value.unshift({
    id: Date.now(), date: new Date().toLocaleString('pt-PT'), op: 'Importar backup',
    user: 'Admin', ok: false, detail: 'Endpoint de restauro não implementado',
  })
  restoring.value = false
  restoreFile.value = null
}
</script>
