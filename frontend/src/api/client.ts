import axios from 'axios'

// Cuando el frontend se abre por un túnel (VS Code Ports / GitHub
// Codespaces) el host cambia cada sesión — no se puede dejar fijo en
// .env. Si el navegador NO está en localhost pero VITE_API_BASE_URL sigue
// apuntando a localhost (o sea, nadie lo actualizó para este túnel), se
// deriva la URL del backend reemplazando el puerto del frontend por el
// del backend en el mismo host — así es como VS Code Ports/Codespaces
// exponen cada puerto reenviado (mismo dominio, puerto embebido).
function resolveApiBaseUrl(): string {
  const configured = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000/api'
  const { hostname, origin } = window.location
  const accessingViaTunnel = hostname !== 'localhost' && hostname !== '127.0.0.1' && configured.includes('localhost')
  if (accessingViaTunnel) {
    return `${origin.replace('5173', '8000')}/api`
  }
  return configured
}

export const apiClient = axios.create({
  baseURL: resolveApiBaseUrl(),
})

let refreshPromise: Promise<string> | null = null

apiClient.interceptors.request.use((config) => {
  const accessToken = localStorage.getItem('nexo_access_token')
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const isAuthEndpoint = originalRequest?.url?.includes('/auth/login/') || originalRequest?.url?.includes('/auth/refresh/')

    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      originalRequest._retry = true
      const refreshToken = localStorage.getItem('nexo_refresh_token')

      if (!refreshToken) {
        handleSessionExpired()
        return Promise.reject(error)
      }

      try {
        if (!refreshPromise) {
          refreshPromise = axios
            .post(`${apiClient.defaults.baseURL}/auth/refresh/`, { refresh: refreshToken })
            .then((res) => {
              const newAccessToken = res.data.access as string
              localStorage.setItem('nexo_access_token', newAccessToken)
              return newAccessToken
            })
            .finally(() => {
              refreshPromise = null
            })
        }
        const newAccessToken = await refreshPromise
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
        return apiClient(originalRequest)
      } catch {
        handleSessionExpired()
        return Promise.reject(error)
      }
    }

    return Promise.reject(error)
  },
)

function handleSessionExpired() {
  localStorage.removeItem('nexo_access_token')
  localStorage.removeItem('nexo_refresh_token')
  window.dispatchEvent(new CustomEvent('nexo:session-expired'))
}
