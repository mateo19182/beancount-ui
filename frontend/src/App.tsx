import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from '@/components/Layout'
import { LedgerGate } from '@/components/LedgerGate'
import { OverviewPage } from '@/pages/OverviewPage'
import { ChartsPage } from '@/pages/ChartsPage'
import { InvestmentsPage } from '@/pages/InvestmentsPage'
import { CryptoPage } from '@/pages/CryptoPage'
import { BanksPage } from '@/pages/BanksPage'
import { TransactionsPage } from '@/pages/TransactionsPage'
import { AddTransactionPage } from '@/pages/AddTransactionPage'
import { ImportPage } from '@/pages/ImportPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<LedgerGate />}>
          <Route element={<Layout />}>
            <Route path="/" element={<OverviewPage />} />
            <Route path="/charts" element={<ChartsPage />} />
            <Route path="/investments" element={<InvestmentsPage />} />
            <Route path="/crypto" element={<CryptoPage />} />
            <Route path="/banks" element={<BanksPage />} />
            <Route path="/transactions" element={<TransactionsPage />} />
            <Route path="/add" element={<AddTransactionPage />} />
            <Route path="/import" element={<ImportPage />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
