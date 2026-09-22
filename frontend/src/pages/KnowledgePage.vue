<template>
  <div class="hd-page knowledge-page">
    <div class="knowledge-head">
      <input class="hd-input" v-model="search" placeholder="Pesquisar artigos..." />
    </div>

    <div v-if="loading" class="state">A carregar...</div>
    <div v-else-if="!filtered.length" class="hd-card state">Ainda não existem artigos publicados.</div>
    <div v-else class="article-grid">
      <article v-for="article in filtered" :key="article.id" class="hd-card article-card">
        <div class="article-top">
          <div v-if="article.category" class="article-category">{{ article.category.name }}</div>
          <button v-if="auth.isAdmin" class="hd-icon-btn article-edit" title="Editar artigo" @click="startEdit(article)">
            <span class="material-icons" style="font-size:16px">edit</span>
          </button>
        </div>
        <h2>{{ article.title }}</h2>
        <p>{{ article.body }}</p>
      </article>
    </div>

    <div v-if="editing" class="kb-backdrop" @click.self="editing = null">
      <div class="hd-card kb-modal">
        <div class="kb-modal-head">
          <div style="font-weight:700;font-size:16px">Editar artigo</div>
          <button class="hd-icon-btn" title="Fechar" @click="editing = null"><span class="material-icons">close</span></button>
        </div>
        <div style="display:flex;flex-direction:column;gap:10px">
          <input class="hd-input" v-model="editing.title" placeholder="Título do artigo" />
          <select class="hd-select" v-model="editing.category_id">
            <option :value="''">Sem categoria</option>
            <option v-for="c in categories" :key="c.id" :value="String(c.id)">{{ c.name }}</option>
          </select>
          <textarea class="hd-textarea" v-model="editing.body" rows="8" placeholder="Conteúdo do artigo"></textarea>
          <label style="display:inline-flex;align-items:center;gap:8px;font-size:13px">
            <input type="checkbox" v-model="editing.is_published" /> Publicado
          </label>
        </div>
        <p v-if="editError" style="color:#EF4444;font-size:12px;margin:10px 0 0">{{ editError }}</p>
        <div class="kb-modal-actions">
          <button class="hd-btn hd-btn-outline" @click="editing = null">Cancelar</button>
          <button class="hd-btn hd-btn-primary" :disabled="saving || !editing.title.trim() || !editing.body.trim()" @click="saveEdit">
            {{ saving ? 'A guardar...' : 'Guardar' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getCategories, getKnowledgeArticles, updateKnowledgeArticle, type Category, type KnowledgeArticle } from '../api/tickets'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const categories = ref<Category[]>([])
const editing = ref<{ id: number; title: string; body: string; category_id: string; is_published: boolean } | null>(null)
const saving = ref(false)
const editError = ref('')

function startEdit(a: KnowledgeArticle) {
  editError.value = ''
  editing.value = { id: a.id, title: a.title, body: a.body, category_id: a.category_id ? String(a.category_id) : '', is_published: a.is_published }
  if (!categories.value.length) getCategories().then(c => { categories.value = c }).catch(() => {})
}

async function saveEdit() {
  if (!editing.value) return
  saving.value = true
  editError.value = ''
  try {
    const e = editing.value
    const updated = await updateKnowledgeArticle(e.id, {
      title: e.title.trim(), body: e.body.trim(),
      category_id: e.category_id ? Number(e.category_id) : null,
      is_published: e.is_published,
    })
    if (updated.is_published) {
      const idx = articles.value.findIndex(a => a.id === updated.id)
      if (idx !== -1) articles.value[idx] = updated
    } else {
      articles.value = articles.value.filter(a => a.id !== updated.id)
    }
    editing.value = null
  } catch (err: any) {
    editError.value = err?.response?.data?.detail || 'Não foi possível guardar o artigo.'
  } finally {
    saving.value = false
  }
}

const articles = ref<KnowledgeArticle[]>([])
const loading = ref(true)
const search = ref('')

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return articles.value
  return articles.value.filter(a => `${a.title} ${a.body} ${a.category?.name ?? ''}`.toLowerCase().includes(q))
})

onMounted(async () => {
  try {
    articles.value = await getKnowledgeArticles()
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.knowledge-page { max-width: 1100px; }
.knowledge-head {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 18px;
}
.knowledge-head .hd-input { max-width: 320px; }
.article-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 14px;
}
.article-card { padding: 18px; }
.article-card h2 {
  line-height: 1.3;
  padding-right: 32px;
  font-family: var(--font-sans);
  font-size: 17px;
  font-weight: 800;
  margin-bottom: 8px;
}
.article-card p {
  color: var(--c-muted);
  margin: 0;
  white-space: pre-wrap;
}
.article-card { position: relative; }
.article-top { padding-right: 40px; }
.article-edit { position: absolute; top: 12px; right: 12px; }
.kb-backdrop { position: fixed; inset: 0; z-index: 100; background: rgba(0,0,0,.5); display: grid; place-items: center; padding: 20px; }
.kb-modal { width: min(560px, 100%); max-height: calc(100vh - 40px); overflow-y: auto; padding: 24px; border-radius: 14px; }
.kb-modal-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.kb-modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--c-border); }
.article-category {
  color: var(--c-primary);
  font-size: 12px;
  font-weight: 800;
  margin-bottom: 8px;
}
.state {
  padding: 44px 20px;
  text-align: center;
  color: var(--c-muted);
}
@media (max-width: 720px) {
  .knowledge-head .hd-input {
    max-width: none;
    width: 100%;
  }
}
</style>
