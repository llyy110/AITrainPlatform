import { defineStore } from 'pinia'
import api from '../api'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || null,
    userInfo: JSON.parse(localStorage.getItem('userInfo') || '{}')
  }),
  getters: {
    isLoggedIn: (state) => !!state.token
  },
  actions: {
    async login(loginId, password) {
      const res = await api.post('/user/login', { loginId, password })
      this.token = res.data.access
      this.userInfo = res.data.user
      localStorage.setItem('token', this.token)
      localStorage.setItem('userInfo', JSON.stringify(this.userInfo))
      return res
    },
    async register(username, email, password, code) {
      return await api.post('/user/register', { username, email, password, code })
    },
    logout() {
      this.token = null
      this.userInfo = {}
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
    },
    async updateProfile(data) {
      const res = await api.put('/user/profile', data, {
        headers: { Authorization: `Bearer ${this.token}` }
      })
      this.userInfo = res.data
      localStorage.setItem('userInfo', JSON.stringify(this.userInfo))
      return res
    }
  }
})