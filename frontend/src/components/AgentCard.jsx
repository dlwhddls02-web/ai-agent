import { Bot, Loader2, CheckCircle, XCircle, Clock } from 'lucide-react'

const STATUS_CONFIG = {
  idle:    { color: 'bg-gray-100 text-gray-600 border-gray-200', icon: Clock,       label: '대기중' },
  running: { color: 'bg-blue-50  text-blue-700  border-blue-200', icon: Loader2,    label: '실행중', spin: true },
  error:   { color: 'bg-red-50   text-red-700   border-red-200',  icon: XCircle,    label: '오류' },
  success: { color: 'bg-green-50 text-green-700 border-green-200',icon: CheckCircle, label: '완료' },
}

const AGENT_LABELS = {
  orchestrator:    { name: '오케스트레이터', desc: '전체 상황 판단 및 에이전트 지휘',          emoji: '🎯' },
  customer_agent:  { name: '고객 관리',       desc: '고객 케어·환영·이탈 방지',               emoji: '👥' },
  contract_agent:  { name: '계약 관리',       desc: '만기 갱신·실효 위험 처리',               emoji: '📋' },
  schedule_agent:  { name: '일정 관리',       desc: '상담 일정 알림 발송',                   emoji: '📅' },
  report_agent:    { name: '보고서',          desc: '일일/주간 실적 보고서 발송',              emoji: '📊' },
  marketing_agent: { name: '마케팅',          desc: '인스타·페북·블로그 콘텐츠 자동 생성',     emoji: '📢' },
}

export default function AgentCard({ agentKey, data, onTrigger, loading }) {
  const status = data?.status || 'idle'
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.idle
  const Icon = cfg.icon
  const meta = AGENT_LABELS[agentKey] || { name: agentKey, desc: '', emoji: '🤖' }

  const lastRun = data?.last_run
    ? new Date(data.last_run).toLocaleTimeString('ko-KR')
    : '없음'

  return (
    <div className={`rounded-2xl border-2 p-5 flex flex-col gap-3 shadow-sm transition-all ${cfg.color}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{meta.emoji}</span>
          <div>
            <p className="font-bold text-sm">{meta.name}</p>
            <p className="text-xs opacity-70">{meta.desc}</p>
          </div>
        </div>
        <span className={`flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full border ${cfg.color}`}>
          <Icon size={12} className={cfg.spin ? 'animate-spin' : ''} />
          {cfg.label}
        </span>
      </div>

      {data?.summary && (
        <p className="text-xs leading-relaxed opacity-80 line-clamp-3 bg-white/50 rounded-lg p-2">
          {data.summary}
        </p>
      )}

      <div className="flex items-center justify-between mt-1">
        <span className="text-xs opacity-60">마지막 실행: {lastRun}</span>
        {agentKey !== 'orchestrator' && (
          <button
            onClick={() => onTrigger(agentKey)}
            disabled={loading || status === 'running'}
            className="text-xs px-3 py-1 rounded-lg bg-white/70 hover:bg-white border font-medium transition disabled:opacity-40"
          >
            수동 실행
          </button>
        )}
      </div>
    </div>
  )
}
