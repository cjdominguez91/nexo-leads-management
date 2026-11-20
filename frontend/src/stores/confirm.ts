import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface ConfirmOptions {
  title: string
  message?: string
  confirmText?: string
  cancelText?: string
  danger?: boolean
}

const DEFAULTS: Required<Pick<ConfirmOptions, 'confirmText' | 'cancelText'>> = {
  confirmText: 'Confirmar',
  cancelText: 'Cancelar',
}

export const useConfirmStore = defineStore('confirm', () => {
  const visible = ref(false)
  const options = ref<ConfirmOptions>({ title: '' })
  let resolver: ((value: boolean) => void) | null = null

  function open(opts: ConfirmOptions): Promise<boolean> {
    options.value = { ...DEFAULTS, ...opts }
    visible.value = true
    return new Promise((resolve) => {
      resolver = resolve
    })
  }

  function respond(value: boolean) {
    visible.value = false
    resolver?.(value)
    resolver = null
  }

  return { visible, options, open, respond }
})
