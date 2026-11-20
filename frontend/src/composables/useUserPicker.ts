import type { AsignableUser } from '@/api/leads'
import { useUserPickerStore } from '@/stores/userPicker'

/** `const picked = await pickUser(asignables, 'Reasignar a…'); if (!picked) return` */
export function useUserPicker() {
  const store = useUserPickerStore()
  return (users: AsignableUser[], title?: string) => store.open({ users, title })
}
