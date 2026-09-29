<template>
  <div class="hd-page profile-page">
    <section class="hd-card pf-card pf-top">
      <AvatarCircle :name="shortName(auth.user?.display_name) || '?'" size="64" />
      <div class="pf-id">
        <div class="pf-name">{{ auth.user?.display_name }}</div>
        <div class="pf-line"><span class="material-icons">mail</span>{{ auth.user?.email }}</div>
        <div class="pf-line"><span class="material-icons">verified_user</span>{{ auth.user?.role_label || 'Utilizador' }}
          <span v-if="auth.user?.department" class="pf-dept">· {{ auth.user.department }}</span></div>
      </div>
    </section>

    <section class="hd-card pf-card">
      <div class="pf-title">Como o seu nome aparece nos tickets</div>
      <p class="pf-desc">
        O nome vem da sua conta da escola ({{ auth.user?.auth_provider === 'azure' ? 'Microsoft 365' : auth.user?.auth_provider === 'ldap' ? 'Active Directory' : 'conta local' }}).
        Pode mudá-lo aqui — a sincronização automática deixa de o alterar.
        Se escrever no fim <code>Docente-510 - Física e Química</code>, aparece a etiqueta do grupo (ex.: <strong>510 FQ</strong>) ao lado do nome curto.
      </p>
      <label class="pf-label" for="pf-name">Nome</label>
      <input id="pf-name" v-model="name" class="hd-input" maxlength="200" />
      <div class="pf-preview">
        <div class="pf-preview-title">Pré-visualização</div>
        <div class="pf-preview-row">
          <span class="pf-preview-label">Onde há espaço</span>
          <div class="pf-sample wide"><AvatarCircle :name="shortName(name) || '?'" size="26" /><span class="pf-full">{{ name.trim() || '—' }}</span></div>
        </div>
        <div class="pf-preview-row">
          <span class="pf-preview-label">Em listas e telemóvel</span>
          <div class="pf-sample"><AvatarCircle :name="shortName(name) || '?'" size="26" /><span class="pf-short">{{ shortName(name) || '—' }}</span><span v-if="groupTag(name)" class="pf-tag">{{ groupTag(name) }}</span></div>
        </div>
      </div>
      <div v-if="auth.user?.name_locked && auth.user?.directory_name" class="pf-note">
        <span class="material-icons">info</span>
        <span>Está a usar um nome escolhido por si. O nome da conta da escola é <strong>{{ auth.user.directory_name }}</strong>.</span>
      </div>

      <div class="pf-actions">
        <button v-if="auth.user?.name_locked" class="hd-btn hd-btn-outline" type="button" :disabled="saving" @click="resetName">
          <span class="material-icons">undo</span> Usar o nome da conta da escola
        </button>
        <span v-if="saved" class="pf-ok"><span class="material-icons">check_circle</span> Guardado</span>
        <button class="hd-btn hd-btn-primary" type="button" :disabled="saving || !changed" @click="save">
          <span class="material-icons">save</span> {{ saving ? 'A guardar…' : 'Guardar' }}
        </button>
      </div>
    </section>

    <section class="hd-card pf-card pf-links">
      <router-link to="/notificacoes" class="pf-link"><span class="material-icons">tune</span><div><strong>As minhas notificações</strong><small>O que recebe por email e como notificação</small></div><span class="material-icons">chevron_right</span></router-link>
      <button type="button" class="pf-link" @click="auth.toggleDark()"><span class="material-icons">{{ auth.isDark ? 'light_mode' : 'dark_mode' }}</span><div><strong>{{ auth.isDark ? 'Modo claro' : 'Modo escuro' }}</strong><small>Neste dispositivo</small></div><span class="material-icons">chevron_right</span></button>
    </section>
  </div>
</template>

<script setup lang="ts">
// O meu perfil: how my name appears in the tickets (kept by the directory sync once I change it)
import { computed, ref, watch } from 'vue'
import { api } from '../boot/axios'
import AvatarCircle from '../components/AvatarCircle.vue'
import { useAuthStore } from '../stores/auth'
import { notifyError } from '../utils/feedback'
import { groupTag, shortName } from '../utils/names'

const auth = useAuthStore()
const name = ref('')
const saving = ref(false)
const saved = ref(false)

watch(() => auth.user, (u) => {
  if (u) name.value = u.display_name
}, { immediate: true })

const changed = computed(() => !!auth.user && name.value.trim().replace(/\s+/g, ' ') !== auth.user.display_name)

async function send(body: any) {
  saving.value = true
  try {
    auth.user = (await api.put('/api/v1/users/me/profile', body)).data
    saved.value = true
    setTimeout(() => { saved.value = false }, 2500)
  } catch (e) {
    notifyError(e, 'Não foi possível guardar o perfil.')
  } finally {
    saving.value = false
  }
}

const save = () => send({ display_name: name.value })
const resetName = () => send({ reset_name: true })
</script>

<style scoped>
.profile-page { max-width: 820px; display: flex; flex-direction: column; gap: 16px; }
.pf-card { padding: 22px 24px; }
.pf-top { display: flex; align-items: center; gap: 18px; }
.pf-name { font-size: 20px; font-weight: 800; color: var(--c-text); overflow-wrap: anywhere; }
.pf-line { display: flex; align-items: center; gap: 6px; font-size: 13.5px; color: var(--c-muted); margin-top: 4px; }
.pf-line .material-icons { font-size: 16px; }
.pf-dept { color: var(--c-muted); }
.pf-title { font-weight: 700; font-size: 15px; }
.pf-desc { font-size: 13px; color: var(--c-muted); margin: 4px 0 16px; line-height: 1.55; }
.pf-desc code { font-size: 12px; background: var(--c-bg); border: 1px solid var(--c-border); border-radius: 5px; padding: 0 4px; }
.pf-label { display: block; font-size: 12.5px; font-weight: 700; color: var(--c-muted); margin-bottom: 6px; }
.pf-opt { font-weight: 500; }
.pf-preview { margin-top: 14px; border: 1px dashed var(--c-border); border-radius: 12px; padding: 12px 14px; }
.pf-preview-title { font-size: 11px; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; color: var(--c-muted); margin-bottom: 8px; }
.pf-preview-row { display: grid; grid-template-columns: 160px minmax(0, 1fr); align-items: center; gap: 10px; padding: 5px 0; }
.pf-preview-label { font-size: 12.5px; color: var(--c-muted); }
.pf-sample { display: flex; align-items: center; gap: 8px; min-width: 0; font-size: 14px; font-weight: 600; color: var(--c-text); }
.pf-full { overflow-wrap: anywhere; }
.pf-tag { font-size: 10.5px; font-weight: 700; color: var(--c-muted); border: 1px solid var(--c-border); border-radius: 6px; padding: 0 6px; line-height: 17px; }
.pf-note { display: flex; gap: 8px; align-items: flex-start; font-size: 12.5px; color: var(--c-muted); background: var(--c-primary-soft); border-radius: 10px; padding: 10px 12px; margin-top: 12px; }
.pf-note .material-icons { font-size: 17px; color: var(--c-primary); }
.pf-actions { display: flex; justify-content: flex-end; align-items: center; gap: 10px; margin-top: 18px; flex-wrap: wrap; }
.pf-actions .hd-btn:first-child:not(.hd-btn-primary) { margin-right: auto; }
.pf-actions .material-icons { font-size: 16px; }
.pf-ok { color: #16A34A; font-weight: 700; font-size: 13px; display: inline-flex; align-items: center; gap: 4px; }
.pf-ok .material-icons { font-size: 17px; }
.pf-links { padding: 6px; }
.pf-link { display: flex; align-items: center; gap: 12px; width: 100%; padding: 12px 14px; border: 0; background: transparent; border-radius: 12px; color: var(--c-text); text-decoration: none; cursor: pointer; text-align: left; font-size: 14px; }
.pf-link:hover { background: var(--c-primary-soft); }
.pf-link > .material-icons:first-child { color: var(--c-primary); }
.pf-link div { flex: 1; display: flex; flex-direction: column; }
.pf-link small { color: var(--c-muted); font-size: 12px; }
@media (max-width: 600px) { .pf-preview-row { grid-template-columns: 1fr; } .pf-top { flex-direction: column; text-align: center; } .pf-line { justify-content: center; } }
</style>
