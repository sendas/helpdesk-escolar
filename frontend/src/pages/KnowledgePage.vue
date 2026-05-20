<template>
  <div class="hd-page knowledge-page">
    <div class="knowledge-head">
      <input class="hd-input" v-model="search" placeholder="Pesquisar artigos..." />
    </div>

    <div v-if="loading" class="state">A carregar...</div>
    <div v-else-if="!filtered.length" class="hd-card state">Ainda não existem artigos publicados.</div>
    <div v-else class="article-grid">
      <article v-for="article in filtered" :key="article.id" class="hd-card article-card">
        <div v-if="article.category" class="article-category">{{ article.category.name }}</div>
        <h2>{{ article.title }}</h2>
        <p>{{ article.body }}</p>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getKnowledgeArticles, type KnowledgeArticle } from '../api/tickets'

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
