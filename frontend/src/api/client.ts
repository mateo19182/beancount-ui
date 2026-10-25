import type {
  BankBalances,
  BankingStatus,
  ChartBreakdownResponse,
  LedgerMeta,
  LedgerStatus,
  OverviewData,
  PositionsResponse,
  TransactionsResponse,
} from './types'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {}
  if (init?.body && !(init.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...headers, ...(init?.headers as Record<string, string>) },
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const j = await res.json()
      detail = j.detail ?? JSON.stringify(j)
    } catch {
      detail = await res.text()
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () =>
    request<{ status: string; ledger_loaded: boolean; ledger_path: string | null }>('/health'),
  ledgerStatus: () => request<LedgerStatus>('/api/ledger/status'),
  ledgerMeta: () => request<LedgerMeta>('/api/ledger/meta'),
  openLedger: (path: string) =>
    request<{ success: boolean; message: string }>('/api/ledger/open', {
      method: 'POST',
      body: JSON.stringify({ path }),
    }),
  createAccount: (body: { account: string; date?: string; currencies?: string[] }) =>
    request<{ success: boolean; message: string; account: string }>('/api/ledger/accounts', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  reload: () =>
    request<{ valid: boolean; message: string }>('/api/ledger/reload', { method: 'POST' }),
  overview: () => request<OverviewData>('/api/overview'),
  chartsMonths: () => request<{ months: { year: number; month: number }[] }>('/api/charts/months'),
  chartsIncomeExpenses: (dateFrom: string, dateTo: string) =>
    request<{ from: string; to: string; income: number; expenses: number; currency: string }>(
      `/api/charts/income-expenses?date_from=${dateFrom}&date_to=${dateTo}`
    ),
  chartsTrend: (dateFrom: string, dateTo: string) =>
    request<{
      from: string
      to: string
      currency: string
      months: { year: number; month: number; income: number; expenses: number }[]
    }>(`/api/charts/trend?date_from=${dateFrom}&date_to=${dateTo}`),
  chartsBreakdown: (dateFrom: string, dateTo: string, kind: string) =>
    request<ChartBreakdownResponse>(
      `/api/charts/breakdown?date_from=${dateFrom}&date_to=${dateTo}&kind=${kind}`
    ),
  investments: () => request<PositionsResponse>('/api/investments'),
  crypto: () => request<PositionsResponse>('/api/crypto'),
  bankBalances: () => request<BankBalances>('/api/banks/balances'),
  bankFiles: () => request<{ files: { name: string; path: string; size_bytes: number }[] }>('/api/banks'),
  bankFile: (path: string) =>
    request<{ path: string; content: string }>(`/api/banks/file?path=${encodeURIComponent(path)}`),
  transactions: (params: URLSearchParams) =>
    request<TransactionsResponse>(`/api/transactions?${params}`),
  createTransaction: (body: object) =>
    request('/api/transactions', { method: 'POST', body: JSON.stringify(body) }),
  updateTransaction: (body: object) =>
    request('/api/transactions', { method: 'PUT', body: JSON.stringify(body) }),
  deleteTransaction: (body: { id: string }) =>
    request('/api/transactions', { method: 'DELETE', body: JSON.stringify(body) }),
  previewTransaction: (body: object) =>
    request<{ preview: string; message: string; valid: boolean; balance: Record<string, number> }>(
      '/api/transactions/preview',
      { method: 'POST', body: JSON.stringify(body) }
    ),
  uploadDocument: (form: FormData) =>
    request<{ success: boolean; message: string }>('/api/documents', { method: 'POST', body: form }),
  documentUrl: (path: string) => `${API_BASE}/api/documents/${path}`,
  bankingStatus: () => request<BankingStatus>('/api/banking/status'),
  bankingAuthStart: (bank_key: string) =>
    request<{ url: string }>('/api/banking/auth/start', {
      method: 'POST',
      body: JSON.stringify({ bank_key }),
    }),
  bankingAuthComplete: (bank_key: string, code: string) =>
    request<{ success: boolean; accounts: number }>('/api/banking/auth/complete', {
      method: 'POST',
      body: JSON.stringify({ bank_key, code }),
    }),
  bankingAuthRevoke: (bank_key: string) =>
    request(`/api/banking/auth/${bank_key}`, { method: 'DELETE' }),
  bankingFetch: (body: object) =>
    request('/api/banking/fetch', { method: 'POST', body: JSON.stringify(body) }),
  bankingStaged: () =>
    request<{
      transactions: import('./types').StagedTxn[]
      active_count: number
      categories: string[]
    }>('/api/banking/staged'),
  bankingUpdateStaged: (transactions: object[]) =>
    request('/api/banking/staged', {
      method: 'PUT',
      body: JSON.stringify({ transactions }),
    }),
  bankingImport: (body: object) =>
    request<{
      success_count: number
      error_count: number
      balance_errors?: string[]
    }>('/api/banking/import', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  bankingDiscard: (body: object) =>
    request('/api/banking/discard', { method: 'POST', body: JSON.stringify(body) }),
}

export type { LedgerMeta, OverviewData } from './types'
