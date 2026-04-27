import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import { RefreshCw, Zap, Search, ChevronDown } from 'lucide-react'
import ContentCard from '../components/ContentCard'

const TABS = [
  { key: 'all',       label: '전체',        icon: '📋', platform: null },
  { key: 'instagram', label: '인스타그램',  icon: '📸', platform: 'instagram' },
  { key: 'facebook',  label: '페이스북',    icon: '👤', platform: 'facebook' },
  { key: 'naver',     label: '네이버 블로그', icon: '📝', platform: 'naver' },
]

const GENERATE_ROUTES = {
  instagram: '/api/agents/marketing/instagram',
  facebook:  '/api/agents/marketing/facebook',
  naver:     '/api/agents/marketing/naver',
  all:       '/api/agents/marketing/run',
}

const SORT_OPTIONS = [
  { value: 'date_desc', label: '최신순' },
  { value: 'date_asc',  label: '오래된순' },
  { value: 'chars_desc', label: '글자수 많은순' },
]

function EmptyState({ onGenerate, loading }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 gap-4 text-gray-400">
      <span className="text-6xl">📭</span>
      <p className="text-base font-medium text-gray-500">아직 생성된 콘텐츠가 없습니다</p>
      <p className="text-sm">에이전트를 실행하면 콘텐츠가 노션에서 불러와집니다</p>
      <button
        onClick={onGenerate}
        disabled={loading}
        className="mt-2 flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm px-5 py-2.5 rounded-xl font-medium transition disabled:opacity-50"
      >
        <Zap size={15} />
        지금 생성하기
      </button>
    </div>
  )
}

function SkeletonCard() {
  return (
    <div className="rounded-2xl border-2 border-gray-100 bg-white shadow-sm overflow-hidden animate-pulse">
      <div className="h-12 bg-gray-100" />
      <div className="p-4 flex flex-col gap-3">
        <div className="h-4 bg-gray-200 rounded w-3/4" />
        <div className="h-3 bg-gray-100 rounded w-full" />
        <div className="h-3 bg-gray-100 rounded w-5/6" />
        <div className="h-3 bg-gray-100 rounded w-4/6" />
        <div className="flex gap-1 mt-1">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-5 w-16 bg-gray-100 rounded-full" />
          ))}
        </div>
      </div>
      <div className="h-10 bg-gray-50 border-t border-gray-100" />
    </div>
  )
}

export default function MarketingPage() {
  const [activeTab, setActiveTab]         = useState('all')
  const [contents, setContents]           = useState([])
  const [loading, setLoading]             = useState(false)
  const [generating, setGenerating]       = useState(false)
  const [lastRefresh, setLastRefresh]     = useState(null)
  const [searchQuery, setSearchQuery]     = useState('')
  const [sortBy, setSortBy]               = useState('date_desc')
  const [showSortMenu, setShowSortMenu]   = useState(false)
  const [generateMsg, setGenerateMsg]     = useState('')

  const currentTab = TABS.find(t => t.key === activeTab) || TABS[0]

  const fetchContents = useCallback(async () => {
    setLoading(true)
    try {
      const params = { limit: 50 }
      if (currentTab.platform) params.platform = currentTab.platform
      const { data } = await axios.get('/api/agents/marketing/contents', { params })
      setContents(data)
      setLastRefresh(new Date())
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [currentTab.platform])

  useEffect(() => {
    fetchContents()
  }, [fetchContents])

  const handleGenerate = async () => {
    const route = GENERATE_ROUTES[activeTab] || GENERATE_ROUTES.all
    setGenerating(true)
    setGenerateMsg('')
    try {
      await axios.post(route, { focus: '수동 생성' })
      setGenerateMsg('생성 요청됨 — 30초 후 새로고침하세요')
      setTimeout(fetchContents, 30000)
    } catch {
      setGenerateMsg('생성 요청 실패')
    } finally {
      setGenerating(false)
    }
  }

  // 검색 + 정렬 적용
  const processed = [...contents]
    .filter(c => {
      if (!searchQuery) return true
      const q = searchQuery.toLowerCase()
      return (
        c.title?.toLowerCase().includes(q) ||
        c.body?.toLowerCase().includes(q) ||
        c.topic?.toLowerCase().includes(q) ||
        c.hashtags?.toLowerCase().includes(q)
      )
    })
    .sort((a, b) => {
      if (sortBy === 'date_asc')   return new Date(a.date) - new Date(b.date)
      if (sortBy === 'chars_desc') return (b.chars || 0) - (a.chars || 0)
      return new Date(b.date) - new Date(a.date)  // date_desc (기본)
    })

  const tabCounts = Object.fromEntries(
    TABS.map(t => [
      t.key,
      t.key === 'all'
        ? contents.length
        : contents.filter(c => {
            const map = { instagram: '인스타그램', facebook: '페이스북', naver: '네이버블로그' }
            return c.platform === map[t.key]
          }).length,
    ])
  )

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-pink-50">
      {/* 페이지 헤더 */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-2xl">📢</span>
                <h2 className="text-xl font-bold text-gray-900">마케팅 콘텐츠</h2>
              </div>
              <p className="text-sm text-gray-500">
                AI가 자동 생성한 SNS 콘텐츠를 확인하고 복사하세요
              </p>
            </div>

            <div className="flex items-center gap-2 flex-shrink-0">
              {generateMsg && (
                <span className="text-xs text-green-600 bg-green-50 px-3 py-1.5 rounded-full border border-green-200">
                  {generateMsg}
                </span>
              )}
              <button
                onClick={fetchContents}
                disabled={loading}
                className="flex items-center gap-1.5 text-sm text-gray-600 hover:text-gray-900 px-3 py-2 rounded-xl hover:bg-gray-100 transition"
              >
                <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
                새로고침
              </button>
              <button
                onClick={handleGenerate}
                disabled={generating}
                className="flex items-center gap-2 bg-gradient-to-r from-pink-500 to-purple-500 hover:from-pink-600 hover:to-purple-600 text-white text-sm px-4 py-2 rounded-xl font-medium transition disabled:opacity-50 shadow-sm"
              >
                <Zap size={15} />
                {generating ? '생성 중…' : '지금 생성'}
              </button>
            </div>
          </div>

          {/* 플랫폼 탭 */}
          <div className="flex gap-1 mt-5">
            {TABS.map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium transition ${
                  activeTab === tab.key
                    ? 'bg-gray-900 text-white shadow-sm'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <span>{tab.icon}</span>
                {tab.label}
                {tabCounts[tab.key] > 0 && (
                  <span className={`text-xs px-1.5 py-0.5 rounded-full font-semibold ${
                    activeTab === tab.key
                      ? 'bg-white/20 text-white'
                      : 'bg-gray-200 text-gray-600'
                  }`}>
                    {tabCounts[tab.key]}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 검색 + 정렬 바 */}
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="제목, 내용, 해시태그 검색..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm border border-gray-200 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400"
          />
        </div>

        {/* 정렬 드롭다운 */}
        <div className="relative">
          <button
            onClick={() => setShowSortMenu(!showSortMenu)}
            className="flex items-center gap-1.5 text-sm px-3 py-2 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 transition"
          >
            {SORT_OPTIONS.find(s => s.value === sortBy)?.label}
            <ChevronDown size={13} className={`transition ${showSortMenu ? 'rotate-180' : ''}`} />
          </button>
          {showSortMenu && (
            <div className="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-xl shadow-lg z-10 overflow-hidden min-w-36">
              {SORT_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => { setSortBy(opt.value); setShowSortMenu(false) }}
                  className={`w-full text-left px-4 py-2.5 text-sm hover:bg-gray-50 transition ${
                    sortBy === opt.value ? 'text-blue-600 font-medium bg-blue-50' : 'text-gray-700'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {lastRefresh && (
          <span className="text-xs text-gray-400 ml-auto">
            마지막 갱신: {lastRefresh.toLocaleTimeString('ko-KR')}
          </span>
        )}
      </div>

      {/* 콘텐츠 그리드 */}
      <main className="max-w-7xl mx-auto px-6 pb-12">
        {/* 결과 카운트 */}
        {!loading && contents.length > 0 && (
          <p className="text-xs text-gray-400 mb-4">
            {processed.length}개 콘텐츠
            {searchQuery && ` (검색: "${searchQuery}")`}
          </p>
        )}

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
            {[...Array(6)].map((_, i) => <SkeletonCard key={i} />)}
          </div>
        ) : processed.length === 0 ? (
          <EmptyState onGenerate={handleGenerate} loading={generating} />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
            {processed.map(c => (
              <ContentCard key={c.page_id} content={c} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
