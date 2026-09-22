import { ref } from 'vue'
import { getPublicSettings } from '../api/settings'

export type UiDesign = 'modern' | 'classic'

const STORAGE_KEY = 'ui_design'

function readCached(): UiDesign {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'classic' ? 'classic' : 'modern'
  } catch {
    return 'modern'
  }
}

const design = ref<UiDesign>(readCached())
let loaded = false

export function setUiDesign(value: UiDesign) {
  design.value = value
  try { localStorage.setItem(STORAGE_KEY, value) } catch { /* ignore */ }
}

export function useUiDesign() {
  if (!loaded) {
    loaded = true
    getPublicSettings()
      .then(s => setUiDesign(s.ui_design === 'classic' ? 'classic' : 'modern'))
      .catch(() => { loaded = false })
  }
  return design
}
