import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Outlet } from 'react-router-dom'
import { api } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'

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
    refetchInterval: 2000,
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
      <div className="flex min-h-screen items-center justify-center">
        <p>Starting backend...</p>
      </div>
    )
  }

  if (!status?.loaded) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <Card className="max-w-lg w-full">
          <CardTitle>Open ledger</CardTitle>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Copy config.toml.example to config.toml and set ledger_path, or open a file below.
          </p>
          <div className="mt-4 flex flex-col gap-2">
            <Input
              placeholder="/path/to/main.beancount"
              value={path}
              onChange={(e) => setPath(e.target.value)}
            />
            <div className="flex gap-2">
              <Button disabled={!path || opening} onClick={() => openLedger(path)}>
                Open
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
                Browse...
              </Button>
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}
          </div>
        </Card>
      </div>
    )
  }

  return <Outlet />
}
