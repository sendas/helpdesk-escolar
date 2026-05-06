<template>
  <router-view />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'

onMounted(() => {
  localStorage.setItem('dark', '0')
  document.documentElement.classList.remove('dark')
})
</script>
