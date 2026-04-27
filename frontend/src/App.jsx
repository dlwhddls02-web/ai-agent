import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import { RefreshCw, Zap, Bot, LayoutDashboard, Megaphone } from 'lucide-react'
import AgentCard from './components/AgentCard'
import LogFeed from './components/LogFeed'
import MarketingPage from './pages/MarketingPage'

const AGENTS = ['orchestrator', 'customer_agent', 'contract_agent', 'schedule_agent', 'report_agent', 'marketing_agent']
const AGENT_ROUTES = {
  customer_agent:  '/api/agents/customer/run',
  contract_agent:  '/api/agents/contract/run',
  schedule_agent:  '/api/agents/schedule/run',
  report_agent:    '/api/agents/report/run',
  marketing_agent: '/api/agents/marketing/run',
}

const NAV_ITEMS = [
  { key: 'dashboard', label: '대시보드',      Icon: LayoutDashboard },
  { key: 'marketing', label: '마케팅 콘텐츠', Icon: Megaphone },
]

function DashboardPage({ agentStatus, logs, loading, triggerLoading, lastRefresh, activeLogTab, setActiveLogTab, triggerAgent, triggerOrchestrator, refresh }) {
  const runningCount = Object.values(agentStatus).filter(s => s?.status === 'running').length
  const errorCount   = Object.values(agentStatus).filter(s => s?.status === 'error').length

  return (
    <>
      {/* 헤더 우측 액션 버튼 영역 */}
      <div className="flex items-center gap-3">
        {runningCount > 0 && (
          <span className="flex items-center gap-1.5 text-xs bg-blue-100 text-blue-700 px-3 py-1.5 rounded-full font-medium">
            <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse" />
            {runningCount}개 실행중
          </span>
        )}
        {errorCount > 0 && (
          <span className="flex items-center gap-1.5 text-xs bg-red-100 text-red-700 px-3 py-1.5 rounded-full font-medium">
            ⚠ {errorCount}개 오류
          </span>
        )}
        <button
          onClick={triggerOrchestrator}
          disabled={!!triggerLoading}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-xl font-medium transition disabled:opacity-50"
        >
          <Zap size={15} />
          전체 실행
        </button>
        <button
          onClick={refresh}
          disabled={loading}
          className="flex items-center gap-1.5 text-sm text-gray-600 hover:text-gray-900 px-3 py-2 rounded-xl hover:bg-gray-100 transition"
        >
          <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
          새로고침
        </button>
      </div>

      {/* 메인 콘텐츠 */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* 에이전트 상태 카드 그리드 */}
        <section className="mb-10">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
            에이전트 현황
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
            {AGENTS.map((key) => (
              <AgentCard
                key={key}
                agentKey={key}
                data={agentStatus[key]}
                onTrigger={triggerAgent}
                loading={!!triggerLoading}
              />
            ))}
          </div>
        </section>

        {/* 행동 로그 피드 */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
              행동 로그
            </h2>
            {lastRefresh && (
              <span className="text-xs text-gray-400">
                마지막 갱신: {lastRefresh.toLocaleTimeString('ko-KR')}
              </span>
            )}
          </div>

          <div className="flex gap-1 mb-4 flex-wrap">
            {['all', ...AGENTS].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveLogTab(tab)}
                className={`text-xs px-3 py-1.5 rounded-lg font-medium transition ${
                  activeLogTab === tab
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-600 hover:bg-gray-100 border'
                }`}
              >
                {tab === 'all' ? '전체' : tab.replace('_agent', '')}
              </button>
            ))}
          </div>

          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-4 min-h-64">
            <LogFeed logs={logs} />
          </div>
        </section>
      </main>
    </>
  )
}

export default function App() {
  const [page, setPage]                   = useState('dashboard')
  const [agentStatus, setAgentStatus]     = useState({})
  const [logs, setLogs]                   = useState([])
  const [loading, setLoading]             = useState(false)
  const [triggerLoading, setTriggerLoading] = useState('')
  const [lastRefresh, setLastRefresh]     = useState(null)
  const [activeLogTab, setActiveLogTab]   = useState('all')

  const fetchStatus = useCallback(async () => {
    try {
      const { data } = await axios.get('/api/agents/status')
      setAgentStatus(data)
    } catch {}
  }, [])

  const fetchLogs = useCallback(async () => {
    try {
      const params = activeLogTab !== 'all' ? { agent: activeLogTab } : {}
      const { data } = await axios.get('/api/logs/', { params: { limit: 100, ...params } })
      setLogs(data)
    } catch {}
  }, [activeLogTab])

  const refresh = useCallback(async () => {
    setLoading(true)
    await Promise.all([fetchStatus(), fetchLogs()])
    setLastRefresh(new Date())
    setLoading(false)
  }, [fetchStatus, fetchLogs])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, 10000)
    return () => clearInterval(id)
  }, [refresh])

  const triggerOrchestrator = async () => {
    setTriggerLoading('orchestrator')
    try { await axios.post('/api/agents/orchestrator/run') } catch {}
    setTimeout(refresh, 1500)
    setTriggerLoading('')
  }

  const triggerAgent = async (agentKey) => {
    const route = AGENT_ROUTES[agentKey]
    if (!route) return
    setTriggerLoading(agentKey)
    try { await axios.post(route, { focus: '수동 실행' }) } catch {}
    setTimeout(refresh, 1500)
    setTriggerLoading('')
  }

  const runningCount = Object.values(agentStatus).filter(s => s?.status === 'running').length

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* 글로벌 헤더 */}
      <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-6 py-0 flex items-center gap-0">
          {/* 로고 */}
          <div className="flex items-center gap-3 py-4 pr-8 border-r border-gray-100">
            <div className="bg-blue-600 text-white p-2 rounded-xl">
              <Bot size={20} />
            </div>
            <div>
              <h1 className="text-sm font-bold text-gray-900 leading-tight">보험팀 자율 AI 에이전트</h1>
              <p className="text-xs text-gray-400">완전 자율 시스템</p>
            </div>
          </div>

          {/* 네비게이션 탭 */}
          <nav className="flex items-center gap-1 px-4 flex-1">
            {NAV_ITEMS.map(({ key, label, Icon }) => (
              <button
                key={key}
                onClick={() => setPage(key)}
                className={`flex items-center gap-2 px-4 py-2 my-2 rounded-xl text-sm font-medium transition ${
                  page === key
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-500 hover:text-gray-800 hover:bg-gray-50'
                }`}
              >
                <Icon size={15} />
                {label}
                {key === 'dashboard' && runningCount > 0 && (
                  <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                )}
              </button>
            ))}
          </nav>

          {/* 대시보드 페이지 전용 우측 버튼 — 마케팅 페이지는 자체 버튼 가짐 */}
          {page === 'dashboard' && (
            <div className="flex items-center gap-3 py-4 pl-4 border-l border-gray-100">
              <button
                onClick={triggerOrchestrator}
                disabled={!!triggerLoading}
                className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-xl font-medium transition disabled:opacity-50"
              >
                <Zap size={15} />
                전체 실행
              </button>
              <button
                onClick={refresh}
                disabled={loading}
                className="flex items-center gap-1.5 text-sm text-gray-600 hover:text-gray-900 px-3 py-2 rounded-xl hover:bg-gray-100 transition"
              >
                <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
                새로고침
              </button>
            </div>
          )}
        </div>
      </header>

      {/* 페이지 라우팅 */}
      {page === 'dashboard' ? (
        <main className="max-w-7xl mx-auto px-6 py-8">
          {/* 에이전트 상태 카드 그리드 */}
          <section className="mb-10">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
              에이전트 현황
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
              {AGENTS.map((key) => (
                <AgentCard
                  key={key}
                  agentKey={key}
                  data={agentStatus[key]}
                  onTrigger={triggerAgent}
                  loading={!!triggerLoading}
                />
              ))}
            </div>
          </section>

          {/* 행동 로그 피드 */}
          <section>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
                행동 로그
              </h2>
              {lastRefresh && (
                <span className="text-xs text-gray-400">
                  마지막 갱신: {lastRefresh.toLocaleTimeString('ko-KR')}
                </span>
              )}
            </div>

            <div className="flex gap-1 mb-4 flex-wrap">
              {['all', ...AGENTS].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveLogTab(tab)}
                  className={`text-xs px-3 py-1.5 rounded-lg font-medium transition ${
                    activeLogTab === tab
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-gray-600 hover:bg-gray-100 border'
                  }`}
                >
                  {tab === 'all' ? '전체' : tab.replace('_agent', '')}
                </button>
              ))}
            </div>

            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-4 min-h-64">
              <LogFeed logs={logs} />
            </div>
          </section>
        </main>
      ) : (
        <MarketingPage />
      )}
    </div>
  )
}
