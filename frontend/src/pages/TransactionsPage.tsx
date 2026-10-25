import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams, Link } from 'react-router-dom'
import { FileText, Pencil, Trash2, Search } from 'lucide-react'
import { api } from '@/api/client'
import { Money } from '@/lib/privacy-blur'
import type { TransactionRow } from '@/api/types'
import { TransactionForm, formValuesToApiPostings, transactionToFormValues } from '@/components/TransactionForm'
import { PageHeader } from '@/components/PageHeader'
import { LoadingState } from '@/components/LoadingState'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
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

  const toFormValues = (tx: TransactionRow) => transactionToFormValues(tx)

  return (
    <div className="space-y-6">
      <PageHeader
        title="Transactions"
        description="Browse and edit ledger entries"
        action={
          <Link to="/add">
            <Button>New entry</Button>
          </Link>
        }
      />

      <Card className="flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-[var(--color-fg-subtle)]">From</label>
          <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-[var(--color-fg-subtle)]">To</label>
          <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        </div>
        <div className="min-w-64 flex-1 flex-col gap-1">
          <label className="text-xs text-[var(--color-fg-subtle)]">Search</label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-fg-subtle)]" />
            <Input
              className="pl-9"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Payee, narration, account..."
            />
          </div>
        </div>
      </Card>

      {isLoading && <LoadingState rows={2} />}
      {error && <p className="text-[var(--color-expense)]">{String(error)}</p>}

      <p className="text-sm text-[var(--color-fg-muted)]">
        {data?.transactions?.length ?? 0} transactions
      </p>

      {editing && meta && (
        <Card className="border-[var(--color-accent)]/30">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-[var(--color-accent)]">
            Edit transaction
          </h2>
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
                postings: formValuesToApiPostings(values),
              })
            }
          />
          <Button variant="outline" className="mt-4" onClick={() => setEditing(null)}>
            Cancel
          </Button>
        </Card>
      )}

      <div className="space-y-2">
        {data?.transactions?.map((tx) => (
          <Card
            key={tx.id}
            className="p-0 overflow-hidden transition-colors hover:border-[var(--color-border)]"
          >
            <details className="group">
              <summary className="flex cursor-pointer list-none items-center gap-3 px-4 py-3">
                <span className="w-24 shrink-0 text-sm tabular-nums text-[var(--color-fg-muted)]">
                  {tx.date}
                </span>
                <span className="min-w-0 flex-1 truncate font-medium">{tx.payee || '(no payee)'}</span>
                <span className="shrink-0 tabular-nums font-semibold text-[var(--color-fg)]">
                  <Money>{tx.amount_str}</Money>
                </span>
                {tx.has_document && (
                  <Badge variant="muted">
                    <FileText className="mr-1 inline h-3 w-3" />
                    doc
                  </Badge>
                )}
              </summary>
              <div className="border-t border-[var(--color-border-subtle)] px-4 py-3 text-sm">
                {tx.narration && (
                  <p className="mb-2 text-[var(--color-fg-muted)]">{tx.narration}</p>
                )}
                <ul className="space-y-1 font-mono text-xs text-[var(--color-fg-subtle)]">
                  {tx.accounts.map((a) => (
                    <li key={a}>{a}</li>
                  ))}
                </ul>
                {tx.document_path && (
                  <button
                    type="button"
                    className="mt-2 text-xs text-[var(--color-accent)] hover:underline"
                    onClick={() => openDocument(tx.document_path!)}
                  >
                    Open document
                  </button>
                )}
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button variant="outline" size="sm" onClick={() => setEditing(tx)}>
                    <Pencil className="h-3.5 w-3.5" />
                    Edit
                  </Button>
                  <label className="inline-flex cursor-pointer items-center gap-1 rounded-lg border border-[var(--color-border)] px-3 py-1.5 text-xs hover:bg-[var(--color-surface-overlay)]">
                    <FileText className="h-3.5 w-3.5" />
                    Attach
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
                    <Trash2 className="h-3.5 w-3.5" />
                    Delete
                  </Button>
                </div>
              </div>
            </details>
          </Card>
        ))}
      </div>
    </div>
  )
}
