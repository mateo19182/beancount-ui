import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import type { StagedTxn } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'

async function openUrl(url: string) {
  try {
    const { open } = await import('@tauri-apps/plugin-shell')
    await open(url)
  } catch {
    window.open(url, '_blank')
  }
}

export function ImportPage() {
  const qc = useQueryClient()
  const { data: status } = useQuery({ queryKey: ['banking-status'], queryFn: api.bankingStatus })
  const { data: staged, refetch } = useQuery({ queryKey: ['banking-staged'], queryFn: api.bankingStaged })

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

  useEffect(() => {
    if (staged?.transactions) setLocalTxns(staged.transactions)
  }, [staged?.transactions])

  const scheduleSave = (txns: StagedTxn[]) => {
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      api.bankingUpdateStaged(txns).catch(console.error)
    }, 800)
  }

  const updateTxn = (idx: number, patch: Partial<StagedTxn>) => {
    setLocalTxns((prev) => {
      const next = prev.map((t, i) => (i === idx ? { ...t, ...patch } : t))
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
        if (t) edits[idx] = { payee: t.payee, narration: t.narration, category: t.category, direction: t.direction ?? 'auto' }
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

  const active = localTxns.filter((t) => !t.imported && !t.discarded)
  const discarded = localTxns.filter((t) => t.discarded && !t.imported)
  const imported = localTxns.filter((t) => t.imported).slice(-10)

  if (!status?.configured) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">Import</h1>
        <Card>
          <p>Enable Banking is not configured. Add to config.toml (see config.toml.example):</p>
          <pre className="mt-4 overflow-auto rounded bg-gray-100 p-4 text-xs dark:bg-gray-900">
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
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Import</h1>

      <Card>
        <CardTitle>Bank Connections</CardTitle>
        <div className="mt-4 space-y-3">
          {(status?.banks ?? []).map((b: { key: string; name: string; authorized: boolean; accounts: number }) => (
            <div key={b.key} className="flex flex-wrap items-center gap-2">
              <span>
                {b.name} {b.authorized ? `(${b.accounts} accounts)` : '(not connected)'}
              </span>
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
          ))}
        </div>
        {authBank && (
          <div className="mt-4 flex flex-wrap gap-2">
            <Input
              className="min-w-96"
              placeholder="Paste OAuth code or redirect URL"
              value={authCode}
              onChange={(e) => setAuthCode(e.target.value)}
            />
            <Button onClick={() => authComplete.mutate()}>Complete auth</Button>
          </div>
        )}
      </Card>

      <Card>
        <CardTitle>Fetch Transactions</CardTitle>
        <div className="mt-4 flex flex-wrap gap-3">
          <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          <div className="flex flex-wrap gap-2">
            {(status?.banks ?? [])
              .filter((b: { authorized: boolean }) => b.authorized)
              .map((b: { key: string; name: string }) => (
                <label key={b.key} className="flex items-center gap-1 text-sm">
                  <input
                    type="checkbox"
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
            Fetch
          </Button>
        </div>
      </Card>

      <Card>
        <CardTitle>Review ({active.length} staged)</CardTitle>
        <div className="mt-4 overflow-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left">
                <th></th>
                <th>Date</th>
                <th>Payee</th>
                <th>Narration</th>
                <th>Amount</th>
                <th>Category</th>
                <th>Dup</th>
                <th>Dir</th>
              </tr>
            </thead>
            <tbody>
              {localTxns.map((txn, idx) => {
                if (txn.imported || txn.discarded) return null
                return (
                  <tr
                    key={txn.id || idx}
                    className={txn.duplicate ? 'bg-yellow-50 dark:bg-yellow-950' : ''}
                  >
                    <td>
                      <input
                        type="checkbox"
                        checked={selectedRows.has(idx)}
                        onChange={(e) => {
                          const next = new Set(selectedRows)
                          if (e.target.checked) next.add(idx)
                          else next.delete(idx)
                          setSelectedRows(next)
                        }}
                      />
                    </td>
                    <td>{txn.date}</td>
                    <td>
                      <Input
                        className="h-8 min-w-32"
                        value={txn.payee}
                        onChange={(e) => updateTxn(idx, { payee: e.target.value })}
                      />
                    </td>
                    <td>
                      <Input
                        className="h-8 min-w-32"
                        value={txn.narration}
                        onChange={(e) => updateTxn(idx, { narration: e.target.value })}
                      />
                    </td>
                    <td className={txn.amount > 0 ? 'text-green-600' : 'text-red-600'}>
                      {txn.amount.toFixed(2)} {txn.currency}
                    </td>
                    <td>
                      <select
                        className="h-8 min-w-48 rounded border px-1 text-xs dark:border-gray-700"
                        value={txn.category}
                        onChange={(e) => updateTxn(idx, { category: e.target.value })}
                      >
                        <option value="">--</option>
                        {(staged?.categories ?? []).map((c: string) => (
                          <option key={c} value={c}>
                            {c}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="max-w-24 truncate text-xs">{txn.duplicate}</td>
                    <td>
                      <select
                        className="h-8 rounded border px-1 text-xs"
                        value={txn.direction ?? 'auto'}
                        onChange={(e) => updateTxn(idx, { direction: e.target.value })}
                      >
                        <option value="auto">auto</option>
                        <option value="reverse">reverse</option>
                      </select>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        <div className="mt-4 flex gap-2">
          <Button
            onClick={() => importMut.mutate()}
            disabled={importMut.isPending || selectedRows.size === 0}
          >
            Import Selected
          </Button>
          <Button
            variant="destructive"
            onClick={() => discardMut.mutate()}
            disabled={selectedRows.size === 0}
          >
            Discard Selected
          </Button>
        </div>
        {importMut.data && (
          <p className="mt-2 text-sm">
            Imported: {importMut.data.success_count}, errors: {importMut.data.error_count}
          </p>
        )}
      </Card>

      {discarded.length > 0 && (
        <Card>
          <CardTitle>Discarded ({discarded.length})</CardTitle>
          <ul className="mt-2 space-y-1 text-sm">
            {localTxns.map((txn, idx) => {
              if (!txn.discarded || txn.imported) return null
              return (
                <li key={idx} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={selectedRows.has(idx)}
                    onChange={(e) => {
                      const next = new Set(selectedRows)
                      if (e.target.checked) next.add(idx)
                      else next.delete(idx)
                      setSelectedRows(next)
                    }}
                  />
                  {txn.date} {txn.payee} {txn.amount.toFixed(2)} {txn.currency}
                </li>
              )
            })}
          </ul>
          <Button
            className="mt-2"
            variant="outline"
            size="sm"
            onClick={() => restoreMut.mutate([...selectedRows])}
          >
            Restore Selected
          </Button>
        </Card>
      )}

      {imported.length > 0 && (
        <Card>
          <CardTitle>Recently imported</CardTitle>
          <ul className="mt-2 space-y-1 text-sm text-gray-600">
            {imported.map((txn) => (
              <li key={txn.id}>
                {txn.date} {txn.payee} {txn.amount.toFixed(2)} {txn.currency}
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  )
}
