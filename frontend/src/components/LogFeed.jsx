import { AlertCircle, Info, CheckCircle } from 'lucide-react'

const LEVEL_CONFIG = {
  info:  { icon: Info,         color: 'text-blue-500' },
  error: { icon: AlertCircle,  color: 'text-red-500'  },
  warn:  { icon: AlertCircle,  color: 'text-yellow-500' },
}

const AGENT_COLORS = {
  orchestrator:   'bg-purple-100 text-purple-700',
  customer_agent: 'bg-blue-100   text-blue-700',
  contract_agent: 'bg-orange-100 text-orange-700',
  schedule_agent: 'bg-green-100  text-green-700',
  report_agent:   'bg-pink-100   text-pink-700',
  kakao_client:   'bg-yellow-100 text-yellow-700',
}

function formatDetail(detail) {
  if (!detail) return null
  if (typeof detail === 'string') return detail
  try { return JSON.stringify(detail, null, 2) } catch { return String(detail) }
}

export default function LogFeed({ logs }) {
  if (!logs || logs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-gray-400">
        <span className="text-4xl mb-2">📭</span>
        <p>아직 로그가 없습니다</p>
        <p className="text-sm">에이전트를 실행하면 여기에 행동 기록이 표시됩니다</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-2">
      {logs.map((log) => {
        const cfg = LEVEL_CONFIG[log.level] || LEVEL_CONFIG.info
        const Icon = cfg.icon
        const agentColor = AGENT_COLORS[log.agent] || 'bg-gray-100 text-gray-600'
        const time = new Date(log.timestamp).toLocaleTimeString('ko-KR')
        const detail = formatDetail(log.detail)

        return (
          <div key={log.id} className="flex gap-3 p-3 rounded-xl hover:bg-gray-50 transition group">
            <Icon size={16} className={`mt-0.5 flex-shrink-0 ${cfg.color}`} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${agentColor}`}>
                  {log.agent}
                </span>
                <span className="text-sm font-medium text-gray-800 truncate">{log.action}</span>
                <span className="text-xs text-gray-400 ml-auto">{time}</span>
              </div>
              {detail && (
                <p className="text-xs text-gray-500 mt-1 truncate group-hover:whitespace-normal group-hover:truncate-none transition-all">
                  {detail}
                </p>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
