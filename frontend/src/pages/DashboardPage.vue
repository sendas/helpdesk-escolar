<template>
  <DashboardClassic v-if="design === 'classic'" />
  <DashboardModern v-else />
</template>

<script setup lang="ts">
import DashboardClassic from './DashboardClassic.vue'
import DashboardModern from './DashboardModern.vue'
import { useUiDesign } from '../composables/useUiDesign'

const design = useUiDesign()
</script>
