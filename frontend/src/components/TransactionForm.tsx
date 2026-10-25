import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Plus, Trash2, Eye } from 'lucide-react'
import { api } from '@/api/client'
import { FlowToggle } from '@/components/FlowToggle'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { applySimpleFlow, inferSimpleFlow, type Flow } from '@/lib/flow'

export type Posting = { account: string; amount: string; currency: string }

export interface TransactionFormValues {
  date: string
  flag: string
  payee: string
  narration: string
  flow: Flow | 'custom'
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

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-[var(--color-fg-subtle)]">
      {children}
    </label>
  )
}

function toApiPostings(values: TransactionFormValues) {
  const numeric = values.postings.map((p) => ({
    account: p.account,
    amount: Math.abs(parseFloat(p.amount) || 0),
    currency: p.currency,
  }))

  if (values.flow === 'in' || values.flow === 'out') {
    return applySimpleFlow(numeric, values.flow)
  }

  return numeric.map((p, i) => {
    const raw = parseFloat(values.postings[i].amount) || 0
    return { ...p, amount: Math.abs(raw), signed: raw }
  })
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

  const isSimple = values.flow === 'in' || values.flow === 'out'

  const previewMut = useMutation({
    mutationFn: () =>
      api.previewTransaction({
        date: values.date,
        flag: values.flag,
        payee: values.payee || null,
        narration: values.narration || null,
        postings: toApiPostings(values),
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

  const setFlow = (flow: Flow | 'custom') => {
    setValues((prev) => ({ ...prev, flow }))
  }

  return (
    <div className="space-y-6">
      <Card>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <FieldLabel>Date</FieldLabel>
            <Input
              type="date"
              value={values.date}
              onChange={(e) => setValues((v) => ({ ...v, date: e.target.value }))}
            />
          </div>
          <div>
            <FieldLabel>Flag</FieldLabel>
            <Select
              value={values.flag}
              onChange={(e) => setValues((v) => ({ ...v, flag: e.target.value }))}
            >
              <option value="*">*</option>
              <option value="!">!</option>
            </Select>
          </div>
          <div>
            <FieldLabel>Payee</FieldLabel>
            <Input
              value={values.payee}
              onChange={(e) => setValues((v) => ({ ...v, payee: e.target.value }))}
              placeholder="Who paid / received"
            />
          </div>
          <div>
            <FieldLabel>Narration</FieldLabel>
            <Input
              value={values.narration}
              onChange={(e) => setValues((v) => ({ ...v, narration: e.target.value }))}
              placeholder="Description"
            />
          </div>
        </div>
      </Card>

      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle>Postings</CardTitle>
          <div className="flex items-center gap-2">
            <FlowToggle
              value={values.flow === 'in' ? 'in' : 'out'}
              onChange={(f) => setFlow(f)}
              size="md"
            />
            <Button
              variant={values.flow === 'custom' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFlow('custom')}
            >
              Custom signs
            </Button>
          </div>
        </div>
        {!isSimple && (
          <p className="mt-2 text-xs text-[var(--color-fg-subtle)]">
            Enter signed amounts (negative = credit to account in beancount terms).
          </p>
        )}
        {isSimple && (
          <p className="mt-2 text-xs text-[var(--color-fg-subtle)]">
            Out = money left your bank. In = money entered your bank. Amounts are positive.
          </p>
        )}
        <div className="mt-4 space-y-3">
          {values.postings.map((p, i) => (
            <div
              key={i}
              className="grid gap-2 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface)] p-3 md:grid-cols-[2fr_1fr_1fr_auto]"
            >
              <div>
                {i === 0 && <FieldLabel>Account</FieldLabel>}
                <Input
                  list="txn-accounts"
                  value={p.account}
                  onChange={(e) => updatePosting(i, 'account', e.target.value)}
                  placeholder="Assets:..."
                />
              </div>
              <div>
                {i === 0 && <FieldLabel>Amount</FieldLabel>}
                <Input
                  type="number"
                  min={isSimple ? 0 : undefined}
                  value={p.amount}
                  onChange={(e) => updatePosting(i, 'amount', e.target.value)}
                  placeholder={isSimple ? '0.00' : '+50 or -50'}
                />
              </div>
              <div>
                {i === 0 && <FieldLabel>Currency</FieldLabel>}
                <Input
                  list="txn-currencies"
                  value={p.currency}
                  onChange={(e) => updatePosting(i, 'currency', e.target.value)}
                />
              </div>
              {values.postings.length > 2 && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="self-end"
                  onClick={() =>
                    setValues((v) => ({ ...v, postings: v.postings.filter((_, idx) => idx !== i) }))
                  }
                >
                  <Trash2 className="h-4 w-4 text-[var(--color-expense)]" />
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
            onClick={() => {
              setFlow('custom')
              setValues((v) => ({
                ...v,
                postings: [
                  ...v.postings,
                  { account: '', amount: '', currency: defaultCurrency },
                ],
              }))
            }}
          >
            <Plus className="h-4 w-4" />
            Add posting
          </Button>
        </div>
      </Card>

      <div className="flex flex-wrap gap-2">
        <Button variant="outline" onClick={() => previewMut.mutate()} disabled={previewMut.isPending}>
          <Eye className="h-4 w-4" />
          Preview
        </Button>
        <Button onClick={() => onSubmit(values)} disabled={pending}>
          {submitLabel}
        </Button>
      </div>

      {message && <p className="text-sm text-[var(--color-fg-muted)]">{message}</p>}
      {preview && (
        <Card>
          <CardTitle>Beancount preview</CardTitle>
          <pre className="beancount-preview mt-3 overflow-auto rounded-lg bg-[var(--color-surface)] p-4 font-mono text-xs text-[var(--color-accent)]">
            {preview}
          </pre>
        </Card>
      )}
    </div>
  )
}

export function transactionToFormValues(tx: {
  date: string
  flag: string
  payee: string
  narration: string
  accounts: string[]
  posting_amounts: { amount: number; currency: string; signed?: number }[]
}): TransactionFormValues {
  const postings = tx.posting_amounts.map((p, i) => ({
    account: tx.accounts[i] ?? '',
    amount:
      p.signed != null
        ? String(p.signed)
        : p.amount >= 0
          ? String(p.amount)
          : String(-p.amount),
    currency: p.currency,
  }))
  const withSigned = tx.posting_amounts.map((p, i) => ({
    account: tx.accounts[i] ?? '',
    signed: p.signed ?? p.amount,
  }))
  const flow = inferSimpleFlow(withSigned)
  return {
    date: tx.date,
    flag: tx.flag,
    payee: tx.payee,
    narration: tx.narration,
    flow,
    postings:
      flow === 'custom'
        ? postings
        : postings.map((p) => ({ ...p, amount: String(Math.abs(parseFloat(p.amount) || 0)) })),
  }
}

export function formValuesToApiPostings(values: TransactionFormValues) {
  return toApiPostings(values)
}
