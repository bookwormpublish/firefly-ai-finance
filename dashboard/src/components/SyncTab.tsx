import { useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

interface Props {
  onSyncComplete: () => void
}

interface SyncResult {
  processed: number
  categorized: number
  flagged_for_review: number
  results: Array<{
    transaction_id: string
    description: string
    amount: number
    category: string
    confidence: number
    needs_review: boolean
  }>
}

export function SyncTab({ onSyncComplete }: Props) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<SyncResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pages, setPages] = useState(1)

  const handleSync = async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await fetch(`${API_URL}/sync-categories?pages=${pages}`, {
        method: 'POST',
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`)
      const data = await res.json()
      setResult(data)
      onSyncComplete()
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const confidenceColor = (c: number) => {
    if (c >= 0.9) return 'text-emerald-400'
    if (c >= 0.7) return 'text-blue-400'
    return 'text-amber-400'
  }

  return (
    <div className="space-y-6">
      {/* Sync Control Panel */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-xl font-bold mb-2">AI Categorization Sync</h2>
        <p className="text-gray-400 text-sm mb-6">
          Fetch uncategorized transactions from Firefly III, send them to Claude for categorization,
          and push categories back automatically.
        </p>

        <div className="flex items-end gap-4 flex-wrap">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Pages to fetch</label>
            <input
              type="number"
              min={1}
              max={10}
              value={pages}
              onChange={e => setPages(Number(e.target.value))}
              className="w-24 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
            <p className="text-xs text-gray-500 mt-1">~20 transactions per page</p>
          </div>

          <button
            onClick={handleSync}
            disabled={loading}
            className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg font-medium transition-colors flex items-center gap-2"
          >
            {loading ? (
              <>
                <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></span>
                Syncing...
              </>
            ) : (
              <>✅ Run AI Sync</>
            )}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-900/30 border border-red-500/50 rounded-xl p-4">
          <p className="text-red-400 font-medium">Sync failed</p>
          <p className="text-gray-400 text-sm mt-1">{error}</p>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Summary */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-emerald-900/20 border border-emerald-500/30 rounded-xl p-4 text-center">
              <p className="text-3xl font-bold text-emerald-400">{result.categorized}</p>
              <p className="text-sm text-gray-400 mt-1">Categorized</p>
            </div>
            <div className="bg-amber-900/20 border border-amber-500/30 rounded-xl p-4 text-center">
              <p className="text-3xl font-bold text-amber-400">{result.flagged_for_review}</p>
              <p className="text-sm text-gray-400 mt-1">Needs Review</p>
            </div>
            <div className="bg-blue-900/20 border border-blue-500/30 rounded-xl p-4 text-center">
              <p className="text-3xl font-bold text-blue-400">{result.processed}</p>
              <p className="text-sm text-gray-400 mt-1">Processed</p>
            </div>
          </div>

          {/* Transaction list */}
          {result.results.length > 0 && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
              <div className="px-5 py-4 border-b border-gray-800">
                <h3 className="font-semibold">Categorization Results</h3>
              </div>
              <div className="divide-y divide-gray-800">
                {result.results.map((r, i) => (
                  <div key={i} className="px-5 py-3 flex items-center justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{r.description}</p>
                      <p className="text-xs text-gray-400">${r.amount.toFixed(2)}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="px-2 py-1 bg-gray-800 rounded-full text-xs font-medium">
                        {r.category}
                      </span>
                      <span className={`text-xs font-mono ${confidenceColor(r.confidence)}`}>
                        {(r.confidence * 100).toFixed(0)}%
                      </span>
                      {r.needs_review && (
                        <span className="text-xs text-amber-400 bg-amber-900/30 px-2 py-0.5 rounded-full">
                          review
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
