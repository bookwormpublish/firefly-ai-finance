import type { Tab } from '../App'

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: 'overview',    label: 'Overview',    icon: '📊' },
  { id: 'categories', label: 'Categories',  icon: '🏷️' },
  { id: 'patterns',   label: 'Patterns',    icon: '🔄' },
  { id: 'sync',       label: 'AI Sync',     icon: '✨' },
]

interface Props {
  activeTab: Tab
  onTabChange: (tab: Tab) => void
}

export function Header({ activeTab, onTabChange }: Props) {
  return (
    <header className="bg-gray-900 border-b border-gray-800 sticky top-0 z-10">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-emerald-500 rounded-lg flex items-center justify-center text-sm font-bold">
              $
            </div>
            <div>
              <h1 className="font-bold text-white leading-none">Firefly AI Finance</h1>
              <p className="text-xs text-gray-500">Powered by Claude</p>
            </div>
          </div>

          {/* Nav tabs */}
          <nav className="flex items-center gap-1">
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`
                  flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all
                  ${
                    activeTab === tab.id
                      ? 'bg-emerald-600 text-white'
                      : 'text-gray-400 hover:text-white hover:bg-gray-800'
                  }
                `}
              >
                <span>{tab.icon}</span>
                <span className="hidden sm:inline">{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>
      </div>
    </header>
  )
}
