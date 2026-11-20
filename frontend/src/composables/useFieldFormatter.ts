import type { CampaignFieldDataType } from '@/api/campaigns'

export function formatFieldValue(value: unknown, dataType: CampaignFieldDataType): string {
  if (value === null || value === undefined || value === '') return '—'

  if (dataType === 'MULTISELECT' && Array.isArray(value)) {
    return value.join(', ')
  }
  if (dataType === 'BOOLEANO') {
    return value ? 'Sí' : 'No'
  }
  if (dataType === 'NUMERO' && typeof value === 'number') {
    return value.toLocaleString('es-PE')
  }
  return String(value)
}
