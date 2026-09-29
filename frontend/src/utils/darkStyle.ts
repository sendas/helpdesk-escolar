// Look of the dark mode, chosen by an administrator in Configurações → Aparência: dark grey (default) or true black
// (pure #000, easier on OLED screens). Cached so the page does not flash grey before the settings arrive.
export type DarkStyle = 'grey' | 'black'

const KEY = 'dark_style'

export function applyDarkStyle(style?: DarkStyle | string | null) {
  const value: DarkStyle = style === 'black' ? 'black' : 'grey'
  document.documentElement.classList.toggle('true-black', value === 'black')
  try { localStorage.setItem(KEY, value) } catch { /* private mode */ }
}

export function applyCachedDarkStyle() {
  let cached: string | null = null
  try { cached = localStorage.getItem(KEY) } catch { /* private mode */ }
  applyDarkStyle(cached)
}
