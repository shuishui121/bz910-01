import { defineStore } from 'pinia'
import http from '../api/http.js'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null'),
  }),
  getters: {
    isCoach: (s) => s.user?.role === 'coach',
    isParent: (s) => s.user?.role === 'parent',
    isAdmin: (s) => s.user?.role === 'admin',
  },
  actions: {
    async login(username, password) {
      const data = await http.post('/auth/login', { username, password })
      this.token = data.token
      this.user = data.user
      localStorage.setItem('token', data.token)
      localStorage.setItem('user', JSON.stringify(data.user))
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    },
  },
})
