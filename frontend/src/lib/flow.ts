export type Flow = 'in' | 'out'

export interface FlowPosting {
  account: string
  signed: number
  currency: string
}

export function migrateLegacyDirection(txn: { direction?: string; flow?: string }): Flow {
  if (txn.flow === 'in' || txn.flow === 'out') return txn.flow
  if (txn.direction === 'positive' || txn.direction === 'reverse') return 'in'
  return 'out'
}

export function buildImportPostings(
  category: string,
  bankAccount: string,
  amount: number,
  currency: string,
  flow: Flow
): FlowPosting[] {
  const amt = Math.abs(amount)
  if (flow === 'in') {
    return [
      { account: category, signed: -amt, currency },
      { account: bankAccount, signed: amt, currency },
    ]
  }
  return [
    { account: category, signed: amt, currency },
    { account: bankAccount, signed: -amt, currency },
  ]
}

export function formatSignedAmount(signed: number, currency: string): string {
  const prefix = signed >= 0 ? '+' : ''
  return `${prefix}${signed.toFixed(2)} ${currency}`
}

export function flowLabel(flow: Flow): string {
  return flow === 'in' ? 'In' : 'Out'
}

export function suggestFlowFromCategory(category: string): Flow | null {
  if (category.startsWith('Expenses:')) return 'out'
  if (category.startsWith('Income:')) return 'in'
  return null
}

export function isBankAccount(account: string): boolean {
  const lower = account.toLowerCase()
  return account.startsWith('Assets:') && (lower.includes('bank') || lower.includes('checking') || lower.includes('savings'))
}

export function applySimpleFlow(
  postings: { account: string; amount: number; currency: string }[],
  flow: Flow
): { account: string; amount: number; currency: string; signed: number }[] {
  if (postings.length !== 2) {
    return postings.map((p) => ({
      ...p,
      amount: Math.abs(p.amount),
      signed: p.amount,
    }))
  }

  return postings.map((posting) => {
    const amt = Math.abs(posting.amount)
    const bank = isBankAccount(posting.account)
    let signed: number

    if (flow === 'out') {
      if (bank) signed = -amt
      else if (posting.account.startsWith('Income:')) signed = -amt
      else signed = amt
    } else if (bank) signed = amt
    else if (posting.account.startsWith('Expenses:')) signed = -amt
    else signed = -amt

    return { ...posting, amount: amt, signed }
  })
}

export function inferSimpleFlow(
  postings: { account: string; signed?: number }[]
): Flow | 'custom' {
  if (postings.length !== 2) return 'custom'
  for (const posting of postings) {
    if (posting.signed == null) continue
    if (isBankAccount(posting.account)) {
      return posting.signed > 0 ? 'in' : 'out'
    }
  }
  return 'custom'
}
