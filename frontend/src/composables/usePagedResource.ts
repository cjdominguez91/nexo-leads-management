import type { Ref } from 'vue'
import { ref } from 'vue'

export interface PagedResourceParams {
  search: string
  ordering: string
  page: number
}

export interface PagedResult<T> {
  count: number
  results: T[]
}

/** Estado de tabla server-side: búsqueda (debounced), orden y paginación —
 * cada cambio dispara un nuevo fetch, sin acumular resultados en cliente. */
export function usePagedResource<T>(
  fetcher: (params: PagedResourceParams) => Promise<PagedResult<T>>,
  defaultOrdering = '',
) {
  const search = ref('')
  const ordering = ref(defaultOrdering)
  const page = ref(1)
  const pageSize = ref(25)
  const items = ref<T[]>([]) as Ref<T[]>
  const count = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)
  let searchDebounce: ReturnType<typeof setTimeout> | null = null

  async function load() {
    loading.value = true
    error.value = null
    try {
      const res = await fetcher({ search: search.value, ordering: ordering.value, page: page.value })
      items.value = res.results
      count.value = res.count
    } catch (err: any) {
      error.value = err?.response?.data?.detail ?? 'No se pudo cargar.'
    } finally {
      loading.value = false
    }
  }

  function setSearch(value: string) {
    search.value = value
    if (searchDebounce) clearTimeout(searchDebounce)
    searchDebounce = setTimeout(() => {
      page.value = 1
      load()
    }, 350)
  }

  function setOrdering(value: string) {
    ordering.value = value
    page.value = 1
    load()
  }

  function setPage(value: number) {
    page.value = value
    load()
  }

  return { search, ordering, page, pageSize, items, count, loading, error, load, setSearch, setOrdering, setPage }
}
