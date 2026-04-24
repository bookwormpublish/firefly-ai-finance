import { useState, useEffect, useCallback } from 'react'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export function useFinanceData(days = 30) {
  const [insights, setInsights] = useState<any>(null)
  const [categorySummary, setCategorySummary] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [insightsRes, summaryRes] = await Promise.all([
        fetch(`${API_URL}/insights?days=${days}`),
        fetch(`${API_URL}/categories/summary?days=${days}`),
      ])

      if (!insightsRes.ok && insightsRes.status !== 404) {
        throw new Error(`Insights API error: ${insightsRes.status}`)
      }
      if (!summaryRes.ok) {
        throw new Error(`Summary API error: ${summaryRes.status}`)
      }

      const insightsData = insightsRes.ok ? await insightsRes.json() : null
      const summaryData = await summaryRes.json()

      setInsights(insightsData)
      setCategorySummary(summaryData)
    } catch (e: any) {
      setError(e.message || 'Failed to load finance data')
    } finally {
      setLoading(false)
    }
  }, [days])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  return {
    insights,
    categorySummary,
    loading,
    error,
    refetch: fetchData,
  }
}
