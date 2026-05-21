import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { Card, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { formatMoney } from '@/lib/utils'

export function BanksPage() {
  const [tab, setTab] = useState<'balances' | 'files'>('balances')
  const [selectedFile, setSelectedFile] = useState<string | null>(null)

  const { data: balances, isLoading: balLoading, error: balError } = useQuery({
    queryKey: ['bank-balances'],
    queryFn: api.bankBalances,
  })
  const { data: files } = useQuery({ queryKey: ['bank-files'], queryFn: api.bankFiles })
  const { data: fileContent } = useQuery({
    queryKey: ['bank-file', selectedFile],
    queryFn: () => api.bankFile(selectedFile!),
    enabled: !!selectedFile,
  })

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Banks</h1>
      <div className="flex gap-2">
        <Button variant={tab === 'balances' ? 'default' : 'outline'} onClick={() => setTab('balances')}>
          Balances
        </Button>
        <Button variant={tab === 'files' ? 'default' : 'outline'} onClick={() => setTab('files')}>
          Import files
        </Button>
      </div>

      {tab === 'balances' && (
        <>
          {balLoading && <p>Loading...</p>}
          {balError && <p className="text-red-600">{String(balError)}</p>}
          {balances && (
            <>
              <Card>
                <CardTitle>Total Bank Balance</CardTitle>
                <p className="mt-2 text-2xl font-bold">
                  {formatMoney(balances.total, balances.currency)}
                </p>
              </Card>
              <Card>
                <CardTitle>Accounts</CardTitle>
                <table className="mt-4 w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th>Account</th>
                      <th className="text-right">Value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {balances.accounts.map((acc) => (
                      <tr key={acc.account} className="border-b border-gray-100 dark:border-gray-800">
                        <td className="py-2">
                          <details>
                            <summary className="cursor-pointer">{acc.account}</summary>
                            <ul className="mt-1 text-xs text-gray-500">
                              {acc.positions.map((p) => (
                                <li key={p.currency}>
                                  {p.amount.toLocaleString()} {p.currency} (
                                  {formatMoney(p.value, balances.currency)})
                                </li>
                              ))}
                            </ul>
                          </details>
                        </td>
                        <td className="py-2 text-right">
                          {formatMoney(acc.value, balances.currency)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            </>
          )}
        </>
      )}

      {tab === 'files' && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardTitle>Bank transaction files</CardTitle>
            <ul className="mt-4 space-y-1 text-sm">
              {(files?.files ?? []).map((f) => (
                <li key={f.path}>
                  <button
                    type="button"
                    className="text-blue-600 hover:underline dark:text-blue-400"
                    onClick={() => setSelectedFile(f.path)}
                  >
                    {f.name}
                  </button>
                  <span className="text-gray-500"> ({(f.size_bytes / 1024).toFixed(1)} KB)</span>
                </li>
              ))}
            </ul>
            {!files?.files?.length && <p className="mt-4 text-gray-500">No bank files found.</p>}
          </Card>
          {selectedFile && fileContent && (
            <Card>
              <CardTitle>{fileContent.path}</CardTitle>
              <pre className="mt-2 max-h-96 overflow-auto text-xs">{fileContent.content}</pre>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
