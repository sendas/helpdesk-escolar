<template>
  <div>
    <template v-if="sent">
      <p class="nac-done">
        <span class="material-icons">check_circle</span>
        Mensagem enviada. Vamos entrar em contacto assim que possível.
      </p>
      <div class="modal-actions">
        <button class="hd-btn hd-btn-primary" type="button" @click="emit('close')">Fechar</button>
      </div>
    </template>
    <template v-else>
      <div class="nac-profiles" role="radiogroup" aria-label="Quem é">
        <button v-for="p in PROFILES" :key="p.key" type="button" class="nac-profile" :class="{ on: form.profile === p.key }"
                role="radio" :aria-checked="form.profile === p.key" @click="form.profile = p.key">
          <span class="material-icons">{{ p.icon }}</span>{{ p.label }}
        </button>
      </div>
      <p class="nac-hint">
        <template v-if="isStudent">Preencha os seus dados de aluno. Se tiver um email (seu ou do encarregado de educação), indique-o para lhe podermos responder.</template>
        <template v-else>Preencha os seus dados. Vamos responder para o email que indicar (pode ser o seu email pessoal).</template>
      </p>
      <div v-if="error" class="nac-error">{{ error }}</div>
      <div class="nac-fields">
        <input v-model="form.name" class="hd-input" :placeholder="isStudent ? 'Nome do aluno' : form.profile === 'docente' ? 'Nome do docente' : 'Nome'" />
        <template v-if="isStudent">
          <input v-model="form.student_number" class="hd-input" :class="{ invalid: form.student_number && !studentNumberValid }"
                 placeholder="Número do cartão de aluno (ex.: a12345)" autocapitalize="off" />
          <div class="nac-row">
            <select v-model="form.year" class="hd-select">
              <option value="" disabled>Ano</option>
              <option v-for="y in YEARS" :key="y" :value="y">{{ y }}</option>
            </select>
            <input v-model="form.class_name" class="hd-input" placeholder="Turma (ex.: B)" maxlength="10" />
          </div>
        </template>
        <input v-model="form.email" class="hd-input" type="email" autocomplete="email"
               :placeholder="isStudent ? 'Email para resposta (opcional)' : 'Email para resposta (obrigatório)'" />
        <input v-model="form.phone" class="hd-input" type="tel" autocomplete="tel" placeholder="Contacto telefónico" />
        <input v-if="form.profile === 'docente'" v-model="form.recruitment_group" class="hd-input" placeholder="Grupo de recrutamento (ex: 550)" />
        <input v-model="form.school" class="hd-input" :placeholder="isStudent ? 'Escola que frequenta' : form.profile === 'docente' ? 'Escola onde leciona' : 'Escola onde trabalha'" />
        <textarea v-model="form.message" class="hd-textarea" rows="4" placeholder="Mensagem"></textarea>
      </div>
      <div class="modal-actions">
        <button class="hd-btn hd-btn-outline" type="button" @click="emit('close')">Cancelar</button>
        <button class="hd-btn hd-btn-primary" type="button" :disabled="sending || !canSend" @click="submit">
          <span class="material-icons" style="font-size:16px">{{ sending ? 'hourglass_empty' : 'send' }}</span>
          {{ sending ? 'A enviar...' : 'Enviar' }}
        </button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
// "Não tenho acesso ao mail institucional" on the login screen, for docentes, não docentes and alunos
import { computed, ref } from 'vue'
import { sendNoAccessContact } from '../api/auth'
import { errorMessage } from '../utils/feedback'

const emit = defineEmits<{ (e: 'close'): void }>()
const PROFILES = [
  { key: 'docente', label: 'Docente', icon: 'school' },
  { key: 'nao_docente', label: 'Não docente', icon: 'badge' },
  { key: 'aluno', label: 'Aluno', icon: 'backpack' },
]
const YEARS = ['5.º', '6.º', '7.º', '8.º', '9.º', '10.º', '11.º', '12.º']
const form = ref({ profile: 'docente', name: '', email: '', phone: '', recruitment_group: '', school: '', message: '',
  student_number: '', year: '', class_name: '' })
const sending = ref(false)
const sent = ref(false)
const error = ref('')

const isStudent = computed(() => form.value.profile === 'aluno')
const emailValid = computed(() => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.value.email.trim()))
const studentNumberValid = computed(() => /^a\d{3,8}$/i.test(form.value.student_number.trim()))
const canSend = computed(() => {
  const f = form.value
  if (!f.name.trim() || !f.message.trim()) return false
  if (isStudent.value) return studentNumberValid.value && !!f.year && !!f.class_name.trim() && !!f.school.trim() && (!f.email.trim() || emailValid.value)
  return emailValid.value
})

async function submit() {
  if (sending.value || !canSend.value) return
  sending.value = true
  error.value = ''
  const f = form.value
  try {
    await sendNoAccessContact({
      profile: f.profile, name: f.name.trim(), email: f.email.trim(), phone: f.phone.trim(),
      recruitment_group: f.profile === 'docente' ? f.recruitment_group.trim() : '', school: f.school.trim(), message: f.message.trim(),
      student_number: isStudent.value ? f.student_number.trim().toLowerCase() : '', year: isStudent.value ? f.year : '',
      class_name: isStudent.value ? f.class_name.trim().toUpperCase() : '',
    })
    sent.value = true
  } catch (e) {
    error.value = errorMessage(e, 'Não foi possível enviar a mensagem. Tente novamente.')
  } finally {
    sending.value = false
  }
}
</script>

<style scoped>
.nac-profiles { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-bottom: 12px; }
.nac-profile { display: inline-flex; flex-direction: column; align-items: center; gap: 2px; border: 1px solid var(--c-border); background: var(--c-surface); color: var(--c-text); border-radius: 10px; padding: 8px 4px; font-size: 12.5px; font-weight: 700; cursor: pointer; }
.nac-profile .material-icons { font-size: 20px; color: var(--c-muted); }
.nac-profile.on { border-color: var(--c-primary); background: var(--c-primary-soft); color: var(--c-primary); }
.nac-profile.on .material-icons { color: var(--c-primary); }
.nac-hint { font-size: 12.5px; color: var(--c-muted); margin: 0 0 14px; line-height: 1.5; }
.nac-error { background: #FEF2F2; border: 1px solid #FECACA; border-radius: 8px; padding: 10px 14px; font-size: 13px; color: #DC2626; margin-bottom: 14px; }
.nac-fields { display: flex; flex-direction: column; gap: 10px; }
.nac-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.nac-done { font-size: 13.5px; line-height: 1.6; color: var(--c-text); }
.nac-done .material-icons { font-size: 18px; color: #22C55E; vertical-align: -3px; margin-right: 4px; }
.hd-input.invalid { border-color: #DC2626; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 16px; }
</style>
