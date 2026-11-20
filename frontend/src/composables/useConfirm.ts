import { useConfirmStore } from '@/stores/confirm'
import type { ConfirmOptions } from '@/stores/confirm'

/** `if (!(await confirm({ title: '¿Eliminar?', danger: true }))) return` */
export function useConfirm() {
  const store = useConfirmStore()
  return (opts: ConfirmOptions) => store.open(opts)
}
