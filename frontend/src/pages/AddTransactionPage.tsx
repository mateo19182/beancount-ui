import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import { TransactionForm } from '@/components/TransactionForm'
import { Card, CardTitle } from '@/components/ui/card'

export function AddTransactionPage() {
  const qc = useQueryClient()
  const { data: meta } = useQuery({ queryKey: ['ledger-meta'], queryFn: api.ledgerMeta })
  const [message, setMessage] = useState('')
  const [docFile, setDocFile] = useState<File | null>(null)

  const createMut = useMutation({
    mutationFn: async (body: object) => {
      const result = await api.createTransaction(body) as { success: boolean; message: string }
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

  if (!meta) return <p>Loading...</p>

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Add Transaction</h1>
      <Card>
        <CardTitle>Document (optional)</CardTitle>
        <input
          type="file"
          className="mt-2 text-sm"
          accept=".pdf,.jpg,.jpeg,.png"
          onChange={(e) => setDocFile(e.target.files?.[0] ?? null)}
        />
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
          postings: [
            { account: '', amount: '', currency: meta.base_currency, direction: 'auto' },
            { account: '', amount: '', currency: meta.base_currency, direction: 'auto' },
          ],
        }}
        submitLabel="Save"
        pending={createMut.isPending}
        onSubmit={(values) =>
          createMut.mutate({
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
      {message && <p className="text-sm">{message}</p>}
    </div>
  )
}
