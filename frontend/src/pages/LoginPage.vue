<template>
  <LoginClassic v-if="design === 'classic'" />
  <LoginModern v-else />
</template>

<script setup lang="ts">
import LoginClassic from './LoginClassic.vue'
import LoginModern from './LoginModern.vue'
import { useUiDesign } from '../composables/useUiDesign'

const design = useUiDesign()
</script>
