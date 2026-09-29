import { boot } from 'quasar/wrappers'
import axios from 'axios'

export const api = axios.create({
  baseURL: '',
  timeout: 15000,
})

export default boot(() => {
  api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })

  api.interceptors.response.use(
    (r) => r,
    (error) => {
      // An expired/invalid session sends the user to the login page. Not for the login calls themselves
      // (a wrong password is also a 401 and its message must stay on screen), nor when already there.
      const url = String(error.config?.url ?? '')
      if (error.response?.status === 401 && !url.includes('/api/v1/auth/') && window.location.pathname !== '/login') {
        localStorage.removeItem('token')
        window.location.href = '/login'
      }
      return Promise.reject(error)
    }
  )
})
