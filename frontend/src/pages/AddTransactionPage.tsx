import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import { TransactionForm, formValuesToApiPostings } from '@/components/TransactionForm'
import { PageHeader } from '@/components/PageHeader'
import { Card, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

export function AddTransactionPage() {
  const qc = useQueryClient()
  const { data: meta } = useQuery({ queryKey: ['ledger-meta'], queryFn: api.ledgerMeta })
  const [message, setMessage] = useState('')
  const [docFile, setDocFile] = useState<File | null>(null)

  const createMut = useMutation({
    mutationFn: async (body: object) => {
      const result = (await api.createTransaction(body)) as { success: boolean; message: string }
      if (docFile) {
        const form = new FormData()
        form.append('file', docFile)
        form.append('date', (body as { date: string }).date)
        form.append('payee', (body as { payee: string }).payee ?? '')
        form.append('narration', (body as { narration: string }).narration ?? '')
        form.append('attach', 'true')
        await api.uploadDocument(form)
      }
      return result
    },
    onSuccess: (d) => {
      setMessage(d.message)
      qc.invalidateQueries()
    },
    onError: (e) => setMessage(String(e)),
  })

  if (!meta) return <p className="text-[var(--color-fg-muted)]">Loading...</p>

  return (
    <div className="space-y-8">
      <PageHeader title="New entry" description="Record a transaction in your ledger" />

      <Card>
        <CardTitle>Receipt (optional)</CardTitle>
        <label className="mt-3 flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-[var(--color-border)] py-8 transition-colors hover:border-[var(--color-accent)] hover:bg-[var(--color-accent-glow)]">
          <input
            type="file"
            className="hidden"
            accept=".pdf,.jpg,.jpeg,.png"
            onChange={(e) => setDocFile(e.target.files?.[0] ?? null)}
          />
          <span className="text-sm text-[var(--color-fg-muted)]">
            {docFile ? docFile.name : 'Drop or click to attach PDF / image'}
          </span>
        </label>
      </Card>

      <TransactionForm
        accounts={meta.accounts}
        currencies={meta.currencies}
        defaultCurrency={meta.base_currency}
        initial={{
          date: new Date().toISOString().slice(0, 10),
          flag: '*',
          payee: '',
          narration: '',
          flow: 'out',
          postings: [
            { account: '', amount: '', currency: meta.base_currency },
            { account: '', amount: '', currency: meta.base_currency },
          ],
        }}
        submitLabel="Save to ledger"
        pending={createMut.isPending}
        onSubmit={(values) =>
          createMut.mutate({
            date: values.date,
            flag: values.flag,
            payee: values.payee || null,
            narration: values.narration || null,
            postings: formValuesToApiPostings(values),
          })
        }
      />
      {message && (
        <p
          className={cn(
            'text-sm',
            message.toLowerCase().includes('error') || message.toLowerCase().includes('fail')
              ? 'text-[var(--color-expense)]'
              : 'text-[var(--color-income)]'
          )}
        >
          {message}
        </p>
      )}
    </div>
  )
}
