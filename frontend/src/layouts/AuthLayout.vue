<template>
  <router-view />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'

onMounted(() => {
  const keepDarkOnLogin = localStorage.getItem('darkLoginPreference') === '1'
  localStorage.setItem('dark', keepDarkOnLogin ? '1' : '0')
  document.documentElement.classList.toggle('dark', keepDarkOnLogin)
})
</script>
