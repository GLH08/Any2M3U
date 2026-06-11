import axios from 'axios'
import { ElMessage } from 'element-plus'

export const api = axios.create({
  baseURL: '',
  withCredentials: true,
  headers: { 'X-Requested-With': 'XMLHttpRequest' }
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401) {
      ElMessage.error('Not authenticated')
    } else if (err?.response?.data?.detail) {
      const d = err.response.data.detail
      if (typeof d === 'string') ElMessage.error(d)
      else if (d.code) ElMessage.error(d.code)
    } else {
      ElMessage.error(err.message || 'Request failed')
    }
    return Promise.reject(err)
  }
)
