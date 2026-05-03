<template>
  <q-page class="flex flex-center">
    <div class="text-center">
      <q-spinner-dots color="primary" size="50px" />
      <div class="q-mt-md text-grey">A autenticar com Microsoft...</div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

onMounted(async () => {
  const hash = window.location.hash
  const match = hash.match(/token=([^&]+)/)
  if (match) {
    await auth.handleAzureCallback(match[1])
  } else {
    router.push('/login')
  }
})
</script>
