import { defineStore } from 'pinia'
import { ref } from 'vue'

import type { AsignableUser } from '@/api/leads'

export interface UserPickerOptions {
  title?: string
  users: AsignableUser[]
}

export const useUserPickerStore = defineStore('userPicker', () => {
  const visible = ref(false)
  const title = ref('Buscar ejecutivo')
  const users = ref<AsignableUser[]>([])
  let resolver: ((value: AsignableUser | null) => void) | null = null

  function open(opts: UserPickerOptions): Promise<AsignableUser | null> {
    title.value = opts.title ?? 'Buscar ejecutivo'
    users.value = opts.users
    visible.value = true
    return new Promise((resolve) => {
      resolver = resolve
    })
  }

  function select(user: AsignableUser) {
    visible.value = false
    resolver?.(user)
    resolver = null
  }

  function cancel() {
    visible.value = false
    resolver?.(null)
    resolver = null
  }

  return { visible, title, users, open, select, cancel }
})
