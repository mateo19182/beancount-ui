import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { api } from '@/api/client'
import type { TransactionRow } from '@/api/types'
import { TransactionForm, type TransactionFormValues } from '@/components/TransactionForm'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'

export function TransactionsPage() {
  const [searchParams] = useSearchParams()
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [search, setSearch] = useState('')
  const [editing, setEditing] = useState<TransactionRow | null>(null)
  const qc = useQueryClient()

  useEffect(() => {
    const month = searchParams.get('month')
    const q = searchParams.get('search')
    if (q) setSearch(q)
    if (month) {
      setDateFrom(`${month}-01`)
      const [y, m] = month.split('-').map(Number)
      const last = new Date(y, m, 0).getDate()
      setDateTo(`${month}-${String(last).padStart(2, '0')}`)
    }
  }, [searchParams])

  const params = new URLSearchParams()
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (search) params.set('search', search)

  const { data: meta } = useQuery({ queryKey: ['ledger-meta'], queryFn: api.ledgerMeta })
  const { data, isLoading, error } = useQuery({
    queryKey: ['transactions', dateFrom, dateTo, search],
    queryFn: () => api.transactions(params),
  })

  const remove = useMutation({
    mutationFn: api.deleteTransaction,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['transactions'] }),
  })

  const update = useMutation({
    mutationFn: (body: object) => api.updateTransaction(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['transactions'] })
      setEditing(null)
    },
  })

  const attachDoc = useMutation({
    mutationFn: async ({ tx, file }: { tx: TransactionRow; file: File }) => {
      const form = new FormData()
      form.append('file', file)
      form.append('transaction_id', tx.id)
      form.append('attach', 'true')
      return api.uploadDocument(form)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['transactions'] }),
  })

  const openDocument = async (path: string) => {
    const url = api.documentUrl(path)
    try {
      const { open } = await import('@tauri-apps/plugin-shell')
      await open(url)
    } catch {
      window.open(url, '_blank')
    }
  }

  const toFormValues = (tx: TransactionRow): TransactionFormValues => ({
    date: tx.date,
    flag: tx.flag,
    payee: tx.payee,
    narration: tx.narration,
    postings: tx.posting_amounts.map((p, i) => ({
      account: tx.accounts[i] ?? '',
      amount: String(p.amount),
      currency: p.currency,
      direction: 'auto',
    })),
  })

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Transactions</h1>
      <Card>
        <div className="flex flex-wrap gap-3">
          <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search payee, narration..."
            className="min-w-64"
          />
        </div>
      </Card>

      {isLoading && <p>Loading...</p>}
      {error && <p className="text-red-600">{String(error)}</p>}

      <p className="text-sm text-gray-500">{data?.transactions?.length ?? 0} transactions</p>

      {editing && meta && (
        <Card>
          <h2 className="mb-4 font-medium">Edit transaction</h2>
          <TransactionForm
            accounts={meta.accounts}
            currencies={meta.currencies}
            defaultCurrency={meta.base_currency}
            initial={toFormValues(editing)}
            submitLabel="Save changes"
            pending={update.isPending}
            onSubmit={(values) =>
              update.mutate({
                id: editing.id,
                date: values.date,
                flag: values.flag,
                payee: values.payee || null,
                narration: values.narration || null,
                postings: values.postings.map((p) => ({
                  account: p.account,
                  amount: parseFloat(p.amount) || 0,
                  currency: p.currency,
                  direction: p.direction,
                })),
              })
            }
          />
          <Button variant="outline" className="mt-2" onClick={() => setEditing(null)}>
            Cancel
          </Button>
        </Card>
      )}

      <div className="space-y-2">
        {data?.transactions?.map((tx) => (
          <details
            key={tx.id}
            className="rounded border border-gray-200 p-3 dark:border-gray-800"
          >
            <summary className="cursor-pointer font-medium">
              {tx.date} | {tx.payee || '(no payee)'} | {tx.amount_str}
              {tx.has_document && ' [doc]'}
            </summary>
            <div className="mt-2 space-y-1 text-sm text-gray-600 dark:text-gray-400">
              <p>Narration: {tx.narration}</p>
              {tx.accounts.map((a) => (
                <p key={a}>{a}</p>
              ))}
              {tx.document_path && (
                <button
                  type="button"
                  className="text-blue-600 hover:underline"
                  onClick={() => openDocument(tx.document_path!)}
                >
                  Open document
                </button>
              )}
              <div className="flex flex-wrap gap-2 pt-2">
                <Button variant="outline" size="sm" onClick={() => setEditing(tx)}>
                  Edit
                </Button>
                <label className="inline-flex cursor-pointer items-center rounded-md border border-gray-300 px-3 py-1 text-sm hover:bg-gray-50 dark:border-gray-700">
                  Add doc
                  <input
                    type="file"
                    className="hidden"
                    accept=".pdf,.jpg,.jpeg,.png"
                    onChange={(e) => {
                      const f = e.target.files?.[0]
                      if (f) attachDoc.mutate({ tx, file: f })
                    }}
                  />
                </label>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => {
                    if (confirm('Delete this transaction?')) remove.mutate({ id: tx.id })
                  }}
                >
                  Delete
                </Button>
              </div>
            </div>
          </details>
        ))}
      </div>
    </div>
  )
}
