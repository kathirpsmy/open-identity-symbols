/**
 * Axios API client — automatically attaches JWT from localStorage.
 */
import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('ois_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('ois_token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (email, password) =>
    api.post('/auth/register', { email, password }),

  confirmTotp: (email, totpCode) =>
    api.post('/auth/confirm-totp', { email, totp_code: totpCode }),

  login: (email, password, totpCode) =>
    api.post('/auth/login', { email, password, totp_code: totpCode }),

  resetTotp: () =>
    api.post('/auth/totp/reset'),

  getMe: () =>
    api.get('/auth/me'),
}

// ── Identity ──────────────────────────────────────────────────────────────────
export const identityApi = {
  generate: () => api.post('/identity/generate'),
  getMe: () => api.get('/identity/me'),
  getById: (symbolId) => api.get(`/identity/${encodeURIComponent(symbolId)}`),
}

// ── Profile ───────────────────────────────────────────────────────────────────
export const profileApi = {
  getMe: () => api.get('/profile/me'),
  updateMe: (data, visibility) => api.put('/profile/me', { data, visibility }),
  getPublic: (symbolId) => api.get(`/profile/${encodeURIComponent(symbolId)}`),
}

// ── Search ────────────────────────────────────────────────────────────────────
export const searchApi = {
  search: (q, limit = 20) => api.get('/search', { params: { q, limit } }),
}

// ── Admin ─────────────────────────────────────────────────────────────────────
export const adminApi = {
  listUsers: (skip = 0, limit = 100) =>
    api.get('/admin/users', { params: { skip, limit } }),
  deactivateUser: (userId) =>
    api.patch(`/admin/users/${userId}/deactivate`),
  activateUser: (userId) =>
    api.patch(`/admin/users/${userId}/activate`),
  getAnalytics: () =>
    api.get('/admin/analytics'),
}
