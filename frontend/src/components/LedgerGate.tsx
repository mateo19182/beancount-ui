import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Outlet } from 'react-router-dom'
import { FileText, FolderOpen } from 'lucide-react'
import { api } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'

async function pickLedgerFile(): Promise<string | null> {
  try {
    const { invoke } = await import('@tauri-apps/api/core')
    return await invoke<string | null>('pick_ledger_file')
  } catch {
    return null
  }
}

export function LedgerGate() {
  const qc = useQueryClient()
  const [path, setPath] = useState('')
  const [error, setError] = useState('')
  const [opening, setOpening] = useState(false)

  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ['health'],
    queryFn: api.health,
    staleTime: 60_000,
    refetchInterval: 60_000,
    retry: 10,
  })

  const { data: status } = useQuery({
    queryKey: ['ledger-status'],
    queryFn: api.ledgerStatus,
    enabled: !!health,
    retry: false,
  })

  const openLedger = async (ledgerPath: string) => {
    setOpening(true)
    setError('')
    try {
      await api.openLedger(ledgerPath)
      await qc.invalidateQueries()
    } catch (e) {
      setError(String(e))
    } finally {
      setOpening(false)
    }
  }

  if (healthLoading || !health) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
        <Skeleton className="h-12 w-12 rounded-xl" />
        <p className="text-sm text-[var(--color-fg-muted)]">Starting backend...</p>
      </div>
    )
  }

  if (!status?.loaded) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <Card className="w-full max-w-md">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-[var(--color-accent-glow)]">
            <FileText className="h-6 w-6 text-[var(--color-accent)]" />
          </div>
          <CardTitle>Open your ledger</CardTitle>
          <p className="mt-2 text-sm text-[var(--color-fg-muted)]">
            Set ledger_path in config.toml, or choose a .beancount file below.
          </p>
          <div className="mt-6 flex flex-col gap-3">
            <Input
              placeholder="/path/to/main.beancount"
              value={path}
              onChange={(e) => setPath(e.target.value)}
            />
            <div className="flex gap-2">
              <Button className="flex-1" disabled={!path || opening} onClick={() => openLedger(path)}>
                Open ledger
              </Button>
              <Button
                variant="outline"
                disabled={opening}
                onClick={async () => {
                  const picked = await pickLedgerFile()
                  if (picked) {
                    setPath(picked)
                    await openLedger(picked)
                  }
                }}
              >
                <FolderOpen className="h-4 w-4" />
              </Button>
            </div>
            {error && <p className="text-sm text-[var(--color-expense)]">{error}</p>}
          </div>
        </Card>
      </div>
    )
  }

  return <Outlet />
}
