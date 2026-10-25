export interface LedgerStatus {
  loaded: boolean
  ledger_path: string | null
  base_currency: string | null
  error_count: number
  errors: string[]
}

export interface LedgerMeta {
  ledger_path: string
  base_currency: string
  accounts: string[]
  currencies: string[]
  error_count: number
}

export interface PostingInput {
  account: string
  amount: number
  currency: string
  signed?: number
  direction?: string
}

export interface TransactionRow {
  id: string
  date: string
  flag: string
  payee: string
  narration: string
  amount_str: string
  accounts: string[]
  posting_amounts: { amount: number; currency: string; signed: number; direction: string }[]
  has_document: boolean
  document_path: string | null
}

export interface TransactionsResponse {
  transactions: TransactionRow[]
  accounts: string[]
}

export interface BankBalances {
  total: number
  currency: string
  accounts: {
    account: string
    value: number
    positions: { currency: string; amount: number; value: number }[]
  }[]
}

export interface OverviewData {
  currency: string
  net_worth: number
  total_assets: number
  total_liabilities: number
  categories: {
    category: string
    total: number
    allocation_pct: number
    accounts: { account: string; currency: string; amount: number; value: number }[]
  }[]
}

export interface PositionsResponse {
  total_value: number
  currency: string
  positions: {
    symbol: string
    shares?: number
    amount?: number
    price: number | null
    value: number | null
    account?: string
    allocation_pct?: number
  }[]
}

export interface BankingStatus {
  enabled: boolean
  configured: boolean
  banks: { key: string; name: string; authorized: boolean; accounts: number }[]
}

export interface ChartBreakdownCategory {
  name: string
  total: number
  account?: string
  subcategories?: { name: string; total: number; account?: string }[]
}

export interface ChartBreakdownResponse {
  from: string
  to: string
  kind: string
  currency: string
  categories: ChartBreakdownCategory[]
}

export interface StagedTxn {
  id: string
  date: string
  payee: string
  narration: string
  amount: number
  currency: string
  category: string
  bank: string
  bank_key: string
  status: string
  duplicate?: string
  flow?: 'in' | 'out'
  flow_conflict?: boolean
  flow_manual?: boolean
  imported?: boolean
  discarded?: boolean
}
