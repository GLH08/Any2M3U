import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<{ username: string } | null>(null)
  const initialized = ref(false)

  async function fetchMe() {
    initialized.value = true
    try {
      const r = await api.get('/api/auth/me')
      user.value = r.data
    } catch {
      user.value = null
    }
  }

  return { user, initialized, fetchMe }
})
