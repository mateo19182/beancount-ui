import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link2, Download, RotateCcw, AlertTriangle, Plus } from 'lucide-react'
import { api } from '@/api/client'
import type { StagedTxn } from '@/api/types'
import type { Flow } from '@/lib/flow'
import { PageHeader } from '@/components/PageHeader'
import { FlowToggle } from '@/components/FlowToggle'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import {
  buildImportPostings,
  formatSignedAmount,
  migrateLegacyDirection,
  suggestFlowFromCategory,
} from '@/lib/flow'
import { cn } from '@/lib/utils'
import { Money } from '@/lib/privacy-blur'

async function openUrl(url: string) {
  try {
    const { open } = await import('@tauri-apps/plugin-shell')
    await open(url)
  } catch {
    window.open(url, '_blank')
  }
}

function normalizeTxn(t: StagedTxn): StagedTxn {
  const flow = (t.flow === 'in' || t.flow === 'out' ? t.flow : migrateLegacyDirection(t)) as Flow
  return { ...t, flow }
}

function bankAccountFor(txn: StagedTxn, accounts: string[]): string {
  const bankKey = txn.bank_key?.toLowerCase() ?? ''
  for (const account of accounts) {
    const lower = account.toLowerCase()
    if (
      (bankKey && (lower.includes(bankKey) || lower.includes(bankKey.replace('_', '')))) &&
      (lower.includes('bank') || lower.includes('checking') || lower.includes('asset'))
    ) {
      return account
    }
  }
  return 'Assets:Bank:Unknown'
}

function normalizeAccountPath(raw: string): string {
  return raw
    .split(':')
    .map((p) => p.trim())
    .filter(Boolean)
    .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
    .join(':')
}

export function ImportPage() {
  const qc = useQueryClient()
  const { data: status } = useQuery({ queryKey: ['banking-status'], queryFn: api.bankingStatus })
  const { data: staged, refetch } = useQuery({ queryKey: ['banking-staged'], queryFn: api.bankingStaged })
  const { data: meta } = useQuery({ queryKey: ['ledger-meta'], queryFn: api.ledgerMeta })

  const [authCode, setAuthCode] = useState('')
  const [authBank, setAuthBank] = useState('')
  const [dateFrom, setDateFrom] = useState(() => {
    const d = new Date()
    d.setDate(d.getDate() - 7)
    return d.toISOString().slice(0, 10)
  })
  const [dateTo, setDateTo] = useState(() => new Date().toISOString().slice(0, 10))
  const [selectedBanks, setSelectedBanks] = useState<string[]>([])
  const [selectedRows, setSelectedRows] = useState<Set<number>>(new Set())
  const [localTxns, setLocalTxns] = useState<StagedTxn[]>([])
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [creatingIdx, setCreatingIdx] = useState<number | null>(null)
  const [newCatRoot, setNewCatRoot] = useState<string>('Expenses')
  const [newCatName, setNewCatName] = useState('')
  const [newCatError, setNewCatError] = useState('')

  useEffect(() => {
    if (staged?.transactions) {
      setLocalTxns(staged.transactions.map(normalizeTxn))
    }
  }, [staged?.transactions])

  const scheduleSave = (txns: StagedTxn[]) => {
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      api.bankingUpdateStaged(txns).catch(console.error)
    }, 800)
  }

  const updateTxn = (idx: number, patch: Partial<StagedTxn>, manualFlow = false) => {
    setLocalTxns((prev) => {
      const next = prev.map((t, i) => {
        if (i !== idx) return t
        const updated = { ...t, ...patch }
        if (manualFlow) updated.flow_manual = true
        if (patch.category && !updated.flow_manual) {
          const suggested = suggestFlowFromCategory(patch.category)
          if (suggested) updated.flow = suggested
        }
        return updated
      })
      scheduleSave(next)
      return next
    })
  }

  const authStart = useMutation({
    mutationFn: (bank_key: string) => api.bankingAuthStart(bank_key),
    onSuccess: async (d: { url: string }) => {
      if (d.url) await openUrl(d.url)
    },
  })

  const authComplete = useMutation({
    mutationFn: () => api.bankingAuthComplete(authBank, authCode),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['banking-status'] })
      setAuthCode('')
    },
  })

  const fetchTxns = useMutation({
    mutationFn: () =>
      api.bankingFetch({ date_from: dateFrom, date_to: dateTo, banks: selectedBanks }),
    onSuccess: () => refetch(),
  })

  const importMut = useMutation({
    mutationFn: () => {
      const edits: Record<number, Record<string, string>> = {}
      selectedRows.forEach((idx) => {
        const t = localTxns[idx]
        if (t)
          edits[idx] = {
            payee: t.payee,
            narration: t.narration,
            category: t.category,
            flow: t.flow ?? 'out',
          }
      })
      return api.bankingImport({ indices: [...selectedRows], edits })
    },
    onSuccess: () => {
      refetch()
      setSelectedRows(new Set())
    },
  })

  const discardMut = useMutation({
    mutationFn: () => api.bankingDiscard({ indices: [...selectedRows] }),
    onSuccess: () => {
      refetch()
      setSelectedRows(new Set())
    },
  })

  const restoreMut = useMutation({
    mutationFn: (indices: number[]) => {
      const next = localTxns.map((t, i) =>
        indices.includes(i) ? { ...t, discarded: false } : t
      )
      return api.bankingUpdateStaged(next)
    },
    onSuccess: () => refetch(),
  })

  const createAccountMut = useMutation({
    mutationFn: (vars: { account: string; date: string }) => api.createAccount(vars),
    onSuccess: (_data, vars) => {
      qc.setQueryData(['banking-staged'], (old: { categories?: string[] } | undefined) =>
        old
          ? { ...old, categories: [...(old.categories ?? []), vars.account].sort() }
          : old
      )
      qc.invalidateQueries({ queryKey: ['ledger-meta'] })
    },
  })

  const earliestStagedDate = localTxns
    .filter((t) => !t.imported && !t.discarded)
    .reduce(
      (min, t) => (t.date && t.date < min ? t.date : min),
      new Date().toISOString().slice(0, 10)
    )

  const handleCreateCategory = (idx: number) => {
    const sub = normalizeAccountPath(newCatName)
    if (!sub) {
      setNewCatError('Enter a category name')
      return
    }
    const account = `${newCatRoot}:${sub}`
    createAccountMut.mutate(
      { account, date: earliestStagedDate },
      {
        onSuccess: () => {
          updateTxn(idx, { category: account })
          setCreatingIdx(null)
          setNewCatName('')
          setNewCatError('')
        },
        onError: (err) => setNewCatError((err as Error).message),
      }
    )
  }

  const active = localTxns.filter((t) => !t.imported && !t.discarded)
  const discarded = localTxns.filter((t) => t.discarded && !t.imported)
  const imported = localTxns.filter((t) => t.imported).slice(-10)
  const ledgerAccounts = meta?.accounts ?? []

  if (!status?.configured) {
    return (
      <div className="space-y-6">
        <PageHeader title="Import" description="Bank sync via Enable Banking" />
        <Card>
          <CardTitle>Setup required</CardTitle>
          <p className="mt-2 text-sm text-[var(--color-fg-muted)]">
            Add Enable Banking to config.toml (see config.toml.example):
          </p>
          <pre className="mt-4 overflow-auto rounded-lg bg-[var(--color-surface)] p-4 font-mono text-xs text-[var(--color-fg-muted)]">
            {`[enable_banking]
enabled = true
app_id = "your-app-id"
key_path = "/path/to/private.pem"

[enable_banking.banks.revolut]
name = "Revolut"
country = "ES"`}
          </pre>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <PageHeader title="Import" description="Connect banks, fetch, and review transactions" />

      <Card>
        <CardTitle>Connections</CardTitle>
        <div className="mt-4 space-y-3">
          {(status?.banks ?? []).map(
            (b: { key: string; name: string; authorized: boolean; expired?: boolean; accounts: number }) => (
              <div
                key={b.key}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[var(--color-border-subtle)] px-4 py-3"
              >
                <div className="flex items-center gap-2">
                  <Link2 className="h-4 w-4 text-[var(--color-fg-subtle)]" />
                  <span className="font-medium">{b.name}</span>
                  <Badge variant={b.authorized ? 'income' : 'muted'}>
                    {b.authorized
                      ? `${b.accounts} accounts`
                      : b.expired
                        ? 'Expired — reconnect'
                        : 'Not connected'}
                  </Badge>
                </div>
                {!b.authorized ? (
                  <Button
                    size="sm"
                    onClick={() => {
                      setAuthBank(b.key)
                      authStart.mutate(b.key)
                    }}
                  >
                    Connect
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() =>
                      api.bankingAuthRevoke(b.key).then(() =>
                        qc.invalidateQueries({ queryKey: ['banking-status'] })
                      )
                    }
                  >
                    Disconnect
                  </Button>
                )}
              </div>
            )
          )}
        </div>
        {authBank && (
          <div className="mt-4 space-y-2">
            <div className="flex flex-wrap gap-2">
              <Input
                className="min-w-80 flex-1"
                placeholder="Paste OAuth code or redirect URL"
                value={authCode}
                onChange={(e) => setAuthCode(e.target.value)}
              />
              <Button onClick={() => authComplete.mutate()} disabled={authComplete.isPending}>
                Complete auth
              </Button>
            </div>
            {authComplete.isError && (
              <p className="text-sm text-[var(--color-expense)]">
                {(authComplete.error as Error).message}
              </p>
            )}
            {authComplete.isSuccess && (
              <p className="text-sm text-[var(--color-income)]">
                Connected ({authComplete.data.accounts} accounts)
              </p>
            )}
          </div>
        )}
      </Card>

      <Card>
        <CardTitle>Fetch</CardTitle>
        <div className="mt-4 flex flex-wrap items-end gap-3">
          <div>
            <label className="mb-1 block text-xs text-[var(--color-fg-subtle)]">From</label>
            <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </div>
          <div>
            <label className="mb-1 block text-xs text-[var(--color-fg-subtle)]">To</label>
            <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </div>
          <div className="flex flex-wrap gap-3">
            {(status?.banks ?? [])
              .filter((b: { authorized: boolean }) => b.authorized)
              .map((b: { key: string; name: string }) => (
                <label key={b.key} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    className="accent-[var(--color-accent)]"
                    checked={selectedBanks.includes(b.key)}
                    onChange={(e) =>
                      setSelectedBanks((prev) =>
                        e.target.checked ? [...prev, b.key] : prev.filter((k) => k !== b.key)
                      )
                    }
                  />
                  {b.name}
                </label>
              ))}
          </div>
          <Button onClick={() => fetchTxns.mutate()} disabled={fetchTxns.isPending}>
            <Download className="h-4 w-4" />
            Fetch
          </Button>
        </div>
      </Card>

      <Card>
        <div className="flex items-center justify-between">
          <CardTitle>Review</CardTitle>
          <Badge variant="accent">{active.length} staged</Badge>
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase tracking-wide text-[var(--color-fg-subtle)]">
                <th className="py-2 pr-2" />
                <th className="py-2">Date</th>
                <th className="py-2">Payee</th>
                <th className="py-2">Narration</th>
                <th className="py-2">Amount</th>
                <th className="py-2">Category</th>
                <th className="py-2">Flow</th>
                <th className="py-2">Preview</th>
                <th className="py-2">Dup</th>
              </tr>
            </thead>
            <tbody>
              {localTxns.map((txn, idx) => {
                if (txn.imported || txn.discarded) return null
                const flow = (txn.flow ?? 'out') as Flow
                const absAmount = Math.abs(txn.amount)
                const bank = bankAccountFor(txn, ledgerAccounts)
                const preview =
                  txn.category && flow
                    ? buildImportPostings(txn.category, bank, txn.amount, txn.currency, flow)
                    : []

                return (
                  <tr
                    key={txn.id || idx}
                    className={cn(
                      'border-b border-[var(--color-border-subtle)] align-top',
                      txn.duplicate && 'bg-amber-500/10'
                    )}
                  >
                    <td className="py-2 pr-2">
                      <input
                        type="checkbox"
                        className="accent-[var(--color-accent)]"
                        checked={selectedRows.has(idx)}
                        onChange={(e) => {
                          const next = new Set(selectedRows)
                          if (e.target.checked) next.add(idx)
                          else next.delete(idx)
                          setSelectedRows(next)
                        }}
                      />
                    </td>
                    <td className="py-2 tabular-nums text-[var(--color-fg-muted)]">{txn.date}</td>
                    <td className="py-2">
                      <Input
                        className="h-8 min-w-28"
                        value={txn.payee}
                        onChange={(e) => updateTxn(idx, { payee: e.target.value })}
                      />
                    </td>
                    <td className="py-2">
                      <Input
                        className="h-8 min-w-28"
                        value={txn.narration}
                        onChange={(e) => updateTxn(idx, { narration: e.target.value })}
                      />
                    </td>
                    <td
                      className={cn(
                        'py-2 tabular-nums font-medium',
                        flow === 'in'
                          ? 'text-[var(--color-income)]'
                          : 'text-[var(--color-expense)]'
                      )}
                    >
                      {flow === 'in' ? '+' : '-'}
                      <Money>
                        {absAmount.toFixed(2)} {txn.currency}
                      </Money>
                    </td>
                    <td className="py-2">
                      {creatingIdx === idx ? (
                        <div className="flex flex-col gap-1">
                          <div className="flex gap-1">
                            <Select
                              className="h-8 w-24 text-xs"
                              value={newCatRoot}
                              onChange={(e) => setNewCatRoot(e.target.value)}
                            >
                              <option value="Expenses">Expenses</option>
                              <option value="Income">Income</option>
                            </Select>
                            <Input
                              className="h-8 min-w-32 text-xs"
                              placeholder="Travel"
                              value={newCatName}
                              onChange={(e) => {
                                setNewCatName(e.target.value)
                                setNewCatError('')
                              }}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') handleCreateCategory(idx)
                                if (e.key === 'Escape') {
                                  setCreatingIdx(null)
                                  setNewCatName('')
                                  setNewCatError('')
                                }
                              }}
                              autoFocus
                            />
                          </div>
                          <div className="flex items-center gap-1">
                            <Button
                              size="sm"
                              className="h-7 px-2 text-xs"
                              onClick={() => handleCreateCategory(idx)}
                              disabled={createAccountMut.isPending}
                            >
                              <Plus className="h-3 w-3" />
                              Create
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 px-2 text-xs"
                              onClick={() => {
                                setCreatingIdx(null)
                                setNewCatName('')
                                setNewCatError('')
                              }}
                            >
                              Cancel
                            </Button>
                          </div>
                          {newCatError && (
                            <span className="text-xs text-[var(--color-expense)]">
                              {newCatError}
                            </span>
                          )}
                        </div>
                      ) : (
                        <Select
                          className="h-8 min-w-40 text-xs"
                          value={txn.category}
                          onChange={(e) => {
                            const v = e.target.value
                            if (v === '__new__') {
                              setCreatingIdx(idx)
                              setNewCatRoot(flow === 'in' ? 'Income' : 'Expenses')
                              setNewCatName('')
                              setNewCatError('')
                            } else {
                              updateTxn(idx, { category: v })
                            }
                          }}
                        >
                          <option value="">—</option>
                          <option value="__new__">+ New category…</option>
                          {(staged?.categories ?? []).map((c: string) => (
                            <option key={c} value={c}>
                              {c}
                            </option>
                          ))}
                        </Select>
                      )}
                    </td>
                    <td className="py-2">
                      <div className="flex flex-col gap-1">
                        <FlowToggle
                          value={flow}
                          onChange={(f) => updateTxn(idx, { flow: f }, true)}
                        />
                        {txn.flow_conflict && !txn.flow_manual && (
                          <span className="inline-flex items-center gap-1 text-xs text-amber-500">
                            <AlertTriangle className="h-3 w-3" />
                            Check flow
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="max-w-48 py-2">
                      {preview.length > 0 ? (
                        <ul className="space-y-0.5 font-mono text-[10px] leading-snug text-[var(--color-fg-subtle)]">
                          {preview.map((p) => (
                            <li key={p.account} className="truncate" title={p.account}>
                              {p.account.split(':').slice(-2).join(':')}{' '}
                              <span
                                className={
                                  p.signed >= 0
                                    ? 'text-[var(--color-income)]'
                                    : 'text-[var(--color-expense)]'
                                }
                              >
                                <Money>{formatSignedAmount(p.signed, p.currency)}</Money>
                              </span>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <span className="text-xs text-[var(--color-fg-subtle)]">—</span>
                      )}
                    </td>
                    <td className="max-w-20 truncate py-2 text-xs text-[var(--color-fg-subtle)]">
                      {txn.duplicate}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button
            onClick={() => importMut.mutate()}
            disabled={importMut.isPending || selectedRows.size === 0}
          >
            Import selected ({selectedRows.size})
          </Button>
          <Button
            variant="destructive"
            onClick={() => discardMut.mutate()}
            disabled={selectedRows.size === 0}
          >
            Discard selected
          </Button>
        </div>
        {importMut.data && (
          <p className="mt-2 text-sm text-[var(--color-fg-muted)]">
            Imported {importMut.data.success_count}, errors {importMut.data.error_count}
            {importMut.data.balance_errors?.length ? (
              <span className="block text-[var(--color-expense)]">
                {importMut.data.balance_errors.join('; ')}
              </span>
            ) : null}
          </p>
        )}
      </Card>

      {discarded.length > 0 && (
        <Card>
          <CardTitle>Discarded ({discarded.length})</CardTitle>
          <ul className="mt-3 space-y-2">
            {localTxns.map((txn, idx) => {
              if (!txn.discarded || txn.imported) return null
              return (
                <li key={idx} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    className="accent-[var(--color-accent)]"
                    checked={selectedRows.has(idx)}
                    onChange={(e) => {
                      const next = new Set(selectedRows)
                      if (e.target.checked) next.add(idx)
                      else next.delete(idx)
                      setSelectedRows(next)
                    }}
                  />
                  <span className="text-[var(--color-fg-muted)]">
                    {txn.date} · {txn.payee} ·{' '}
                    <Money>
                      {Math.abs(txn.amount).toFixed(2)} {txn.currency}
                    </Money>
                  </span>
                </li>
              )
            })}
          </ul>
          <Button
            className="mt-3"
            variant="outline"
            size="sm"
            onClick={() => restoreMut.mutate([...selectedRows])}
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Restore selected
          </Button>
        </Card>
      )}

      {imported.length > 0 && (
        <Card>
          <CardTitle>Recently imported</CardTitle>
          <ul className="mt-3 space-y-1 text-sm text-[var(--color-fg-muted)]">
            {imported.map((txn) => (
              <li key={txn.id}>
                {txn.date} {txn.payee}{' '}
                <Money>
                  {Math.abs(txn.amount).toFixed(2)} {txn.currency}
                </Money>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  )
}
