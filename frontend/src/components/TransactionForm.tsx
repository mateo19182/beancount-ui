import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'

export type Posting = { account: string; amount: string; currency: string; direction: string }

export interface TransactionFormValues {
  date: string
  flag: string
  payee: string
  narration: string
  postings: Posting[]
}

interface TransactionFormProps {
  accounts: string[]
  currencies: string[]
  defaultCurrency: string
  initial: TransactionFormValues
  onSubmit: (values: TransactionFormValues) => void
  submitLabel: string
  pending?: boolean
}

export function TransactionForm({
  accounts,
  currencies,
  defaultCurrency,
  initial,
  onSubmit,
  submitLabel,
  pending,
}: TransactionFormProps) {
  const [values, setValues] = useState(initial)
  const [preview, setPreview] = useState('')
  const [message, setMessage] = useState('')

  const previewMut = useMutation({
    mutationFn: () =>
      api.previewTransaction({
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
      }),
    onSuccess: (d) => {
      setPreview(d.preview)
      setMessage(d.message)
    },
  })

  const updatePosting = (i: number, field: keyof Posting, value: string) => {
    setValues((prev) => ({
      ...prev,
      postings: prev.postings.map((p, idx) => (idx === i ? { ...p, [field]: value } : p)),
    }))
  }

  return (
    <div className="space-y-4">
      <Card>
        <div className="grid gap-3 md:grid-cols-4">
          <div>
            <label className="text-sm">Date</label>
            <Input
              type="date"
              value={values.date}
              onChange={(e) => setValues((v) => ({ ...v, date: e.target.value }))}
            />
          </div>
          <div>
            <label className="text-sm">Flag</label>
            <select
              className="h-9 w-full rounded-md border border-gray-300 px-2 text-sm dark:border-gray-700"
              value={values.flag}
              onChange={(e) => setValues((v) => ({ ...v, flag: e.target.value }))}
            >
              <option value="*">*</option>
              <option value="!">!</option>
            </select>
          </div>
          <div>
            <label className="text-sm">Payee</label>
            <Input
              value={values.payee}
              onChange={(e) => setValues((v) => ({ ...v, payee: e.target.value }))}
            />
          </div>
          <div>
            <label className="text-sm">Narration</label>
            <Input
              value={values.narration}
              onChange={(e) => setValues((v) => ({ ...v, narration: e.target.value }))}
            />
          </div>
        </div>
      </Card>

      <Card>
        <CardTitle>Postings</CardTitle>
        <div className="mt-4 space-y-3">
          {values.postings.map((p, i) => (
            <div key={i} className="grid gap-2 md:grid-cols-5">
              <Input
                list="txn-accounts"
                value={p.account}
                onChange={(e) => updatePosting(i, 'account', e.target.value)}
                placeholder="Account"
              />
              <Input
                type="number"
                value={p.amount}
                onChange={(e) => updatePosting(i, 'amount', e.target.value)}
                placeholder="Amount"
              />
              <Input
                list="txn-currencies"
                value={p.currency}
                onChange={(e) => updatePosting(i, 'currency', e.target.value)}
              />
              <select
                className="h-9 rounded-md border border-gray-300 px-2 text-sm dark:border-gray-700"
                value={p.direction}
                onChange={(e) => updatePosting(i, 'direction', e.target.value)}
              >
                <option value="auto">auto</option>
                <option value="normal">normal</option>
                <option value="reverse">reverse</option>
              </select>
              {values.postings.length > 2 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    setValues((v) => ({ ...v, postings: v.postings.filter((_, idx) => idx !== i) }))
                  }
                >
                  Remove
                </Button>
              )}
            </div>
          ))}
          <datalist id="txn-accounts">
            {accounts.map((a) => (
              <option key={a} value={a} />
            ))}
          </datalist>
          <datalist id="txn-currencies">
            {currencies.map((c) => (
              <option key={c} value={c} />
            ))}
          </datalist>
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              setValues((v) => ({
                ...v,
                postings: [
                  ...v.postings,
                  { account: '', amount: '', currency: defaultCurrency, direction: 'auto' },
                ],
              }))
            }
          >
            Add posting
          </Button>
        </div>
      </Card>

      <div className="flex gap-2">
        <Button onClick={() => previewMut.mutate()} disabled={previewMut.isPending}>
          Preview
        </Button>
        <Button onClick={() => onSubmit(values)} disabled={pending}>
          {submitLabel}
        </Button>
      </div>

      {message && <p className="text-sm">{message}</p>}
      {preview && (
        <Card>
          <CardTitle>Preview</CardTitle>
          <pre className="mt-2 overflow-auto text-xs">{preview}</pre>
        </Card>
      )}
    </div>
  )
}
