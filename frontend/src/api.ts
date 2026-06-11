import axios from 'axios'

export const api = axios.create({
  baseURL: '',
  withCredentials: true,
  headers: { 'X-Requested-With': 'XMLHttpRequest' }
})
