import { useEffect, useState } from 'react'
import type { Tab } from '../App'
import { OverviewTab } from './OverviewTab'
import { CategoriesTab } from './CategoriesTab'
import { PatternsTab } from './PatternsTab'
import { SyncTab } from './SyncTab'
import { useFinanceData } from '../hooks/useFinanceData'

interface DashboardProps {
  activeTab: Tab
}

export function Dashboard({ activeTab }: DashboardProps) {
  const { insights, categorySummary, loading, error, refetch } = useFinanceData()

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-400 mx-auto mb-4"></div>
          <p className="text-gray-400">Loading your financial data...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-900/30 border border-red-500/50 rounded-xl p-6 text-center">
        <p className="text-red-400 font-medium">Failed to load data</p>
        <p className="text-gray-400 text-sm mt-1">{error}</p>
        <button
          onClick={refetch}
          className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm font-medium transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div>
      {activeTab === 'overview' && (
        <OverviewTab insights={insights} categorySummary={categorySummary} />
      )}
      {activeTab === 'categories' && (
        <CategoriesTab categorySummary={categorySummary} />
      )}
      {activeTab === 'patterns' && (
        <PatternsTab insights={insights} />
      )}
      {activeTab === 'sync' && (
        <SyncTab onSyncComplete={refetch} />
      )}
    </div>
  )
}
