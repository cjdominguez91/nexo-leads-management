import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import * as notificationsApi from '@/api/notifications'
import type { AppNotification } from '@/api/notifications'

const RECONNECT_DELAY_MS = 3000

export const useNotificationsStore = defineStore('notifications', () => {
  const items = ref<AppNotification[]>([])
  const toasts = ref<AppNotification[]>([])
  let socket: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  const unreadCount = computed(() => items.value.filter((n) => !n.leido).length)

  async function loadHistory() {
    const res = await notificationsApi.fetchNotifications()
    items.value = res.results
  }

  function connect(token: string) {
    if (socket) return
    socket = new WebSocket(notificationsApi.buildNotificationsSocketUrl(token))

    socket.onmessage = (event) => {
      const notification: AppNotification = JSON.parse(event.data)
      items.value = [notification, ...items.value]
      // Persiste hasta que el usuario la cierre con la × — sin auto-dismiss.
      toasts.value = [...toasts.value, notification]
      window.dispatchEvent(new CustomEvent('nexo:notification', { detail: notification }))
    }

    socket.onclose = () => {
      socket = null
      if (reconnectTimer) return
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null
        const current = localStorage.getItem('nexo_access_token')
        if (current) connect(current)
      }, RECONNECT_DELAY_MS)
    }
  }

  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    socket?.close()
    socket = null
    items.value = []
    toasts.value = []
  }

  function dismissToast(id: number) {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  async function marcarLeida(id: number) {
    const notification = items.value.find((n) => n.id === id)
    if (!notification || notification.leido) return
    notification.leido = true
    await notificationsApi.marcarLeida(id)
  }

  async function marcarTodasLeidas() {
    items.value = items.value.map((n) => ({ ...n, leido: true }))
    await notificationsApi.marcarTodasLeidas()
  }

  return {
    items,
    toasts,
    unreadCount,
    loadHistory,
    connect,
    disconnect,
    dismissToast,
    marcarLeida,
    marcarTodasLeidas,
  }
})
