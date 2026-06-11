import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<{ username: string; last_login_at: string | null } | null>(null)
  const initialized = ref(false)
  const needsSetup = ref(false)

  async function fetchMe() {
    initialized.value = true
    try {
      const r = await api.get('/api/auth/me')
      user.value = r.data
      needsSetup.value = false
    } catch (e: any) {
      user.value = null
      if (e?.response?.status === 404 && e?.response?.data?.detail?.code === 'not_initialized') {
        needsSetup.value = true
      }
    }
  }

  async function login(username: string, password: string) {
    const r = await api.post('/api/auth/login', { username, password })
    user.value = r.data
    needsSetup.value = false
  }

  async function logout() {
    await api.post('/api/auth/logout')
    user.value = null
  }

  async function changePassword(oldP: string, newP: string) {
    await api.post('/api/auth/password', { old: oldP, new: newP })
  }

  return { user, initialized, needsSetup, fetchMe, login, logout, changePassword }
})
