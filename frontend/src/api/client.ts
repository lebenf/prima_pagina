import axios from 'axios'

const client = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null
  const match = document.cookie.match(new RegExp('(?:^|; )' + name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '=([^;]*)'))
  return match ? decodeURIComponent(match[1]) : null
}

client.interceptors.request.use(config => {
  const csrf = getCookie('pp_csrf')
  if (csrf && ['post', 'put', 'patch', 'delete'].includes((config.method || '').toLowerCase())) {
    config.headers['X-CSRF-Token'] = csrf
  }
  return config
})

client.interceptors.response.use(
  res => res,
  async err => {
    if (err.response?.status === 401) {
      // Lazy import to avoid circular dependency
      const { useAuthStore } = await import('@/stores/auth')
      const { default: router } = await import('@/router')
      useAuthStore().clearUser()
      await router.push('/login')
    }
    return Promise.reject(err)
  }
)

export default client
