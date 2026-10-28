const API = import.meta.env.VITE_API_URL ?? ''

function cookie(name: string) {
  return document.cookie.split('; ').find((part) => part.startsWith(`${name}=`))?.split('=').slice(1).join('=')
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const method = (options.method ?? 'GET').toUpperCase()
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    let csrf = cookie('agape_csrf')
    if (!csrf) {
      await fetch(`${API}/api/auth/csrf`, { credentials: 'include' })
      csrf = cookie('agape_csrf')
    }
    if (csrf) headers.set('X-CSRF-Token', decodeURIComponent(csrf))
  }
  const response = await fetch(`${API}${path}`, { ...options, headers, credentials: 'include' })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    let detail = typeof payload?.detail === 'string' ? payload.detail : ''
    if (!detail && Array.isArray(payload?.detail)) {
      const fields = new Set(payload.detail.map((issue: { loc?: unknown[] }) => issue.loc?.at(-1)))
      if (fields.has('email')) detail = 'Confira o formato do e-mail informado.'
      else if (fields.has('password')) detail = 'Confira o campo de senha.'
      else detail = 'Confira os dados informados e tente novamente.'
    }
    if (!detail && response.status === 401) detail = 'E-mail ou senha inválidos.'
    if (!detail && response.status === 403) detail = 'Sua verificação de segurança expirou. Atualize a página e tente novamente.'
    if (!detail && response.status === 422) detail = 'Confira os dados informados e tente novamente.'
    if (!detail && response.status === 429) detail = 'Muitas tentativas de acesso. Aguarde um minuto antes de tentar novamente.'
    if (!detail && response.status >= 500) detail = 'O servidor encontrou um problema. Tente novamente em instantes.'
    if (!detail) detail = 'Não foi possível concluir a solicitação.'
    throw new Error(detail)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const money = (amount: string | number) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(amount))

export const dateTime = (value: string) => {
  const normalized = /(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : `${value}Z`
  return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(normalized))
}