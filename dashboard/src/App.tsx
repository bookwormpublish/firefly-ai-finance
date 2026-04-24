import { useState } from 'react'
import { Dashboard } from './components/Dashboard'
import { Header } from './components/Header'
import './index.css'

export type Tab = 'overview' | 'categories' | 'patterns' | 'sync'

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('overview')

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <Header activeTab={activeTab} onTabChange={setActiveTab} />
      <main className="max-w-7xl mx-auto px-4 py-6">
        <Dashboard activeTab={activeTab} />
      </main>
    </div>
  )
}
