/**
 * Configuração da API
 *
 * Todas as requisições passam pelo proxy interno do Next.js (/api/proxy/...).
 * O proxy roda no servidor e injeta o X-API-Key secreto antes de repassar
 * ao backend, garantindo que a chave nunca fique exposta no bundle do cliente.
 */

// Aponta para o proxy interno do Next.js — sem NEXT_PUBLIC_ para não vazar segredos
export const API_BASE_URL = '/api/proxy'

/**
 * Função genérica para fazer requisições à API
 */
export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`

  const defaultHeaders: HeadersInit = {
    'Content-Type': 'application/json',
  }

  // Adicionar token do localStorage se existir
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token')
    if (token) {
      defaultHeaders['Authorization'] = `Bearer ${token}`
    }
  }

  const config: RequestInit = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  }

  try {
    // Timeout de 30 segundos
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 30000)

    const response = await fetch(url, {
      ...config,
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    // Sem conteúdo
    if (response.status === 204) {
      return {} as T
    }

    let data
    try {
      data = await response.json()
    } catch (jsonError) {
      if (!response.ok) {
        const error = new Error(
          `Erro na requisição: ${response.statusText}`
        ) as Error & { status?: number; response?: Response }
        error.status = response.status
        error.response = response
        throw error
      }
      return {} as T
    }

    if (!response.ok) {
      const error = new Error(
        data.error || data.message || `Erro na requisição: ${response.statusText}`
      ) as Error & { status?: number; response?: Response; [key: string]: any }
      error.status = response.status
      error.response = response

      // Copiar campos extras do JSON de erro (ex: pendingWithdrawId, etc.)
      Object.keys(data).forEach((key) => {
        if (key !== 'error' && key !== 'message') {
          ;(error as any)[key] = data[key]
        }
      })

      throw error
    }

    return data
  } catch (error) {
    if (error instanceof Error) {
      // Timeout
      if (error.name === 'AbortError') {
        const timeoutError = new Error(
          'Tempo de espera esgotado. O servidor pode estar indisponível.'
        ) as Error & { status?: number }
        timeoutError.status = 0
        throw timeoutError
      }

      // Erros de rede
      if (
        error.message.includes('Failed to fetch') ||
        error.message.includes('NetworkError') ||
        error.message.includes('Network request failed') ||
        error.message.includes('ECONNREFUSED') ||
        error.message.includes('ERR_CONNECTION_REFUSED') ||
        error.message.includes('ERR_NETWORK_CHANGED')
      ) {
        const networkError = new Error(
          'Servidor indisponível. Verifique sua conexão.'
        ) as Error & { status?: number }
        networkError.status = 0
        throw networkError
      }

      throw error
    }
    throw new Error('Erro desconhecido na requisição')
  }
}

/**
 * GET request
 */
export function apiGet<T>(endpoint: string): Promise<T> {
  return apiRequest<T>(endpoint, { method: 'GET' })
}

/**
 * POST request
 */
export function apiPost<T>(endpoint: string, body?: unknown): Promise<T> {
  return apiRequest<T>(endpoint, {
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
  })
}

/**
 * PUT request
 */
export function apiPut<T>(endpoint: string, body?: unknown): Promise<T> {
  return apiRequest<T>(endpoint, {
    method: 'PUT',
    body: body ? JSON.stringify(body) : undefined,
  })
}

/**
 * DELETE request
 */
export function apiDelete<T>(endpoint: string, body?: unknown): Promise<T> {
  return apiRequest<T>(endpoint, {
    method: 'DELETE',
    body: body ? JSON.stringify(body) : undefined,
  })
}

/**
 * Upload de arquivo
 */
export async function apiUpload<T>(
  endpoint: string,
  file: File,
  fieldName: string = 'file'
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`

  const formData = new FormData()
  formData.append(fieldName, file)

  const defaultHeaders: HeadersInit = {}

  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token')
    if (token) {
      defaultHeaders['Authorization'] = `Bearer ${token}`
    }
  }

  const config: RequestInit = {
    method: 'PUT',
    headers: defaultHeaders,
    body: formData,
  }

  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 30000)

    const response = await fetch(url, {
      ...config,
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.error || `Erro na requisição: ${response.statusText}`)
    }

    return data
  } catch (error) {
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new Error('Tempo de espera esgotado. O servidor pode estar indisponível.')
      }

      if (
        error.message.includes('Failed to fetch') ||
        error.message.includes('NetworkError') ||
        error.message.includes('Network request failed') ||
        error.message.includes('ECONNREFUSED') ||
        error.message.includes('ERR_CONNECTION_REFUSED') ||
        error.message.includes('ERR_NETWORK_CHANGED')
      ) {
        throw new Error('Servidor indisponível. Verifique sua conexão.')
      }

      throw error
    }
    throw new Error('Erro desconhecido na requisição')
  }
}
