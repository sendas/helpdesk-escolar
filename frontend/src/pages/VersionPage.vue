<template>
  <div class="hd-page version-page">
    <div class="version-hero">
      <div>
        <p>Versão atual</p>
        <h1>{{ versionLabelText }}</h1>
      </div>
      <span class="material-icons">new_releases</span>
    </div>

    <div class="release-list">
      <article v-for="release in RELEASE_NOTES" :key="release.version" class="hd-card release-card">
        <div class="release-head">
          <div>
            <h2>v{{ release.version }}</h2>
            <p>{{ release.title }}</p>
          </div>
          <time>{{ release.date }}{{ release.time ? ' ' + release.time : '' }}</time>
        </div>
        <ul>
          <li v-for="change in release.changes" :key="change">
            <span class="material-icons">check_circle</span>
            {{ change }}
          </li>
        </ul>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RELEASE_NOTES, versionLabel } from '../utils/version'

const versionLabelText = versionLabel()
</script>

<style scoped>
.version-page {
  max-width: 920px;
}

.version-hero {
  align-items: center;
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: 10px;
  display: flex;
  justify-content: space-between;
  margin-bottom: 18px;
  padding: 22px 24px;
}

.version-hero p,
.release-head p {
  color: var(--c-muted);
  font-size: 13px;
  margin: 0;
}

.version-hero h1 {
  font-size: 28px;
  margin: 4px 0 0;
}

.version-hero .material-icons {
  color: var(--c-primary);
  font-size: 34px;
}

.release-list {
  display: grid;
  gap: 14px;
}

.release-card {
  padding: 20px;
}

.release-head {
  align-items: start;
  display: flex;
  gap: 16px;
  justify-content: space-between;
  margin-bottom: 14px;
}

.release-head h2 {
  font-size: 18px;
  margin: 0 0 4px;
}

.release-head time {
  color: var(--c-muted);
  font-size: 12px;
  white-space: nowrap;
}

.release-card ul {
  display: grid;
  gap: 9px;
  list-style: none;
  margin: 0;
  padding: 0;
}

.release-card li {
  align-items: start;
  color: var(--c-text);
  display: grid;
  font-size: 13px;
  gap: 8px;
  grid-template-columns: 16px minmax(0, 1fr);
}

.release-card li .material-icons {
  color: #16A34A;
  font-size: 16px;
  margin-top: 1px;
}

@media (max-width: 700px) {
  .version-hero,
  .release-head {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
