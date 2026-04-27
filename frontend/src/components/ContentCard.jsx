import { useState } from 'react'
import { Copy, Check, Calendar, Hash } from 'lucide-react'

const PLATFORM_CONFIG = {
  '인스타그램': {
    icon: '📸',
    badge: 'bg-gradient-to-r from-pink-500 to-purple-500 text-white',
    border: 'border-pink-200',
    header: 'bg-gradient-to-r from-pink-50 to-purple-50',
    tag: 'bg-pink-100 text-pink-700',
  },
  '페이스북': {
    icon: '👤',
    badge: 'bg-blue-600 text-white',
    border: 'border-blue-200',
    header: 'bg-blue-50',
    tag: 'bg-blue-100 text-blue-700',
  },
  '네이버블로그': {
    icon: '📝',
    badge: 'bg-green-600 text-white',
    border: 'border-green-200',
    header: 'bg-green-50',
    tag: 'bg-green-100 text-green-700',
  },
}

const DEFAULT_CONFIG = {
  icon: '📄',
  badge: 'bg-gray-500 text-white',
  border: 'border-gray-200',
  header: 'bg-gray-50',
  tag: 'bg-gray-100 text-gray-600',
}

function CopyButton({ textToCopy, label = '복사' }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    const text = textToCopy || ''
    if (!text) return

    try {
      await navigator.clipboard.writeText(text)
    } catch {
      // clipboard API 미지원 브라우저 폴백
      const el = document.createElement('textarea')
      el.value = text
      el.style.position = 'fixed'
      el.style.opacity = '0'
      document.body.appendChild(el)
      el.focus()
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
    }

    setCopied(true)
    setTimeout(() => setCopied(false), 1000)
  }

  return (
    <button
      onClick={handleCopy}
      disabled={!textToCopy}
      className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg font-medium border transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
        copied
          ? 'bg-green-50 text-green-600 border-green-200'
          : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50 hover:border-gray-300'
      }`}
    >
      {copied ? <Check size={12} /> : <Copy size={12} />}
      {copied ? '✅ 복사됨' : label}
    </button>
  )
}

export default function ContentCard({ content }) {
  const [expanded, setExpanded] = useState(false)

  const cfg = PLATFORM_CONFIG[content.platform] || DEFAULT_CONFIG

  const hashtags = content.hashtags
    ? content.hashtags.split(' ').filter(Boolean)
    : []

  // 복사용 텍스트는 항상 전체 본문 사용 (bodyPreview 아님)
  const fullBody = content.body || ''
  const fullCopyText = [
    content.title || '',
    '',
    fullBody,
    '',
    content.hashtags || '',
  ].filter((line, i, arr) => !(line === '' && arr[i - 1] === '')).join('\n')

  const bodyPreview = content.body
    ? (expanded ? content.body : content.body.slice(0, 200) + (content.body.length > 200 ? '…' : ''))
    : ''

  const dateStr = content.date
    ? new Date(content.date).toLocaleDateString('ko-KR', { month: 'long', day: 'numeric', weekday: 'short' })
    : ''

  return (
    <div className={`rounded-2xl border-2 ${cfg.border} bg-white shadow-sm flex flex-col overflow-hidden`}>
      {/* 카드 헤더 */}
      <div className={`${cfg.header} px-4 py-3 flex items-center justify-between`}>
        <div className="flex items-center gap-2">
          <span className="text-lg">{cfg.icon}</span>
          <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${cfg.badge}`}>
            {content.platform}
          </span>
          {content.topic && (
            <span className="text-xs text-gray-500 font-medium">#{content.topic}</span>
          )}
        </div>
        <div className="flex items-center gap-1.5 text-xs text-gray-400">
          <Calendar size={11} />
          {dateStr}
        </div>
      </div>

      {/* 카드 바디 */}
      <div className="px-4 py-3 flex flex-col gap-3 flex-1">
        {/* 제목 */}
        <h3 className="font-bold text-sm text-gray-900 leading-snug">
          {content.title || '제목 없음'}
        </h3>

        {/* 본문 */}
        {bodyPreview && (
          <div className="relative">
            <p className="text-xs text-gray-600 leading-relaxed whitespace-pre-wrap">
              {bodyPreview}
            </p>
            {content.body && content.body.length > 200 && (
              <button
                onClick={() => setExpanded(!expanded)}
                className="text-xs text-blue-500 hover:text-blue-700 font-medium mt-1"
              >
                {expanded ? '접기' : '더 보기'}
              </button>
            )}
          </div>
        )}

        {/* 해시태그 */}
        {hashtags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {hashtags.slice(0, expanded ? hashtags.length : 6).map((tag, i) => (
              <span
                key={i}
                className={`text-xs px-2 py-0.5 rounded-full font-medium ${cfg.tag}`}
              >
                {tag.startsWith('#') ? tag : `#${tag}`}
              </span>
            ))}
            {!expanded && hashtags.length > 6 && (
              <span className="text-xs text-gray-400 px-1 py-0.5">
                +{hashtags.length - 6}개
              </span>
            )}
          </div>
        )}
      </div>

      {/* 카드 푸터 */}
      <div className="px-4 py-3 border-t border-gray-100 flex items-center justify-between gap-2">
        <span className="text-xs text-gray-400">
          {content.chars ? `${content.chars.toLocaleString()}자` : ''}
        </span>
        <div className="flex items-center gap-2">
          <CopyButton textToCopy={fullBody} label="본문 복사" />
          <CopyButton textToCopy={fullCopyText} label="전체 복사" />
        </div>
      </div>
    </div>
  )
}
