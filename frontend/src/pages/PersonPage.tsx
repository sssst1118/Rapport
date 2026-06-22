/*
 * 人物详情 Person（产品方案 §10.3）—— 点头像进入，「以人为中心」的核心页。
 *
 * 头部：大色块头像 + 名字 + 关系 + 段/句计数。
 * 三个 Tab：
 *   1) 对话历史（事实，真数据）—— 按对话分组、可跳播原声、链到对话页。
 *   2) 人物分析（解读，M4）—— InterpretationCard 占位，列出各解读小节。
 *   3) 你和TA的关系（解读，M4）—— InterpretationCard 占位。
 * 见面前 brief：显眼入口（§10.3），点开拉 getPersonBrief，仍是 M4 占位。
 *
 * 事实/解读分离：对话历史是事实（真数据 + 可回放）；分析/关系/brief 是解读，
 * 只走 InterpretationCard + 占位信封，绝不自己编内容。
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'
import {
  getPerson,
  getPersonAnalysis,
  getPersonBrief,
  getPersonUtterances,
} from '../api/client'
import { useAsync } from '../lib/useAsync'
import { Avatar } from '../components/Avatar'
import { Button } from '../components/Button'
import { InterpretationCard } from '../components/InterpretationCard'
import { LoadingBlock, EmptyState, ErrorState } from '../components/states'
import { PersonTabs, type PersonTab } from './people/PersonTabs'
import { PersonHistoryList } from './people/PersonHistoryList'
// M3 复盘模式（§10.6）：覆盖层，从本页「复盘」按钮以 person 范围打开
import { ReviewOverlay } from './review/ReviewOverlay'

type TabKey = 'history' | 'analysis' | 'relation'

export function PersonPage() {
  const { t } = useTranslation('people')
  const { id = '' } = useParams()

  // Tab 标签走 i18n；interpretation 标记保持原样（决定 M4 微标）
  const TABS: PersonTab[] = [
    { key: 'history', label: t('tabs.history') },
    { key: 'analysis', label: t('tabs.analysis'), interpretation: true },
    { key: 'relation', label: t('tabs.relation'), interpretation: true },
  ]

  const person = useAsync((s) => getPerson(id, s), [id])
  const utterances = useAsync((s) => getPersonUtterances(id, s), [id])
  const analysis = useAsync((s) => getPersonAnalysis(id, s), [id])

  const [tab, setTab] = useState<TabKey>('history')
  // 复盘覆盖层开关（§10.6，person 范围）
  const [reviewOpen, setReviewOpen] = useState(false)
  // 见面前 brief：默认不拉，点开「准备见面」时才请求（按需，且更显眼）
  const [briefOpen, setBriefOpen] = useState(false)
  const brief = useAsync(
    (s) => (briefOpen ? getPersonBrief(id, s) : Promise.resolve(null)),
    [id, briefOpen],
  )

  if (person.loading) return <LoadingBlock label={t('detail.loading')} />
  if (person.error || !person.data)
    return <ErrorState message={t('detail.error')} onRetry={person.reload} />

  const p = person.data

  return (
    <section>
      {/* 头部名片：大头像 + 名字（记录体）+ 关系 + 计数（等宽） */}
      <header className="mb-6 flex items-center gap-4">
        <Avatar person={p} size={64} />
        <div className="min-w-0 flex-1">
          <h1 className="font-record text-2xl font-semibold tracking-tight text-ink">
            {p.name}
          </h1>
          <p className="mt-0.5 font-ui text-sm text-ink-soft">
            {p.relation || t('detail.noRelation')} ·{' '}
            <span className="font-mono">{p.conversation_count}</span>{' '}
            {t('detail.conversationCount', { count: p.conversation_count })} ·{' '}
            <span className="font-mono">{p.utterance_count}</span>{' '}
            {t('detail.utteranceCount', { count: p.utterance_count })}
          </p>
        </div>
        <Button
          variant="secondary"
          className="shrink-0"
          onClick={() => setReviewOpen(true)}
        >
          {t('detail.review')}
        </Button>
      </header>

      {/* 见面前 brief：§10.3 显眼入口。解读层（M4），点开才拉 */}
      <div className="mb-6 rounded-card border border-iris/25 bg-iris-tint/60 p-4">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <h2 className="font-ui text-sm font-semibold text-iris">
              {t('detail.brief.title')}
            </h2>
            <p className="mt-0.5 font-ui text-xs text-ink-soft">
              {t('detail.brief.subtitle', { name: p.name })}
            </p>
          </div>
          {!briefOpen && (
            <Button
              variant="secondary"
              className="shrink-0"
              onClick={() => setBriefOpen(true)}
            >
              {t('detail.brief.cta')}
            </Button>
          )}
        </div>

        {briefOpen && (
          <div className="mt-3">
            <InterpretationCard
              title={t('detail.brief.title')}
              interpretation={brief.data}
              loading={brief.loading}
            />
          </div>
        )}
      </div>

      {/* Tab 切换条 */}
      <PersonTabs
        tabs={TABS}
        active={tab}
        onChange={(k) => setTab(k as TabKey)}
      />

      {/* —— Tab 1：对话历史（事实，真数据）—— */}
      {tab === 'history' && (
        <div
          role="tabpanel"
          id="person-panel-history"
          aria-labelledby="person-tab-history"
        >
          {utterances.loading && (
            <LoadingBlock label={t('detail.history.loading')} />
          )}
          {!utterances.loading && utterances.error && (
            <ErrorState
              message={t('detail.history.error')}
              onRetry={utterances.reload}
            />
          )}
          {!utterances.loading &&
            !utterances.error &&
            utterances.data &&
            utterances.data.length === 0 && (
              <EmptyState
                title={t('detail.history.emptyTitle')}
                hint={t('detail.history.emptyHint')}
              />
            )}
          {!utterances.loading &&
            !utterances.error &&
            utterances.data &&
            utterances.data.length > 0 && (
              <PersonHistoryList
                personId={p.id}
                utterances={utterances.data}
              />
            )}
        </div>
      )}

      {/* —— Tab 2：人物分析（解读，M4）—— */}
      {tab === 'analysis' && (
        <div
          role="tabpanel"
          id="person-panel-analysis"
          aria-labelledby="person-tab-analysis"
          className="space-y-3"
        >
          <p className="font-ui text-sm text-ink-soft">
            {t('detail.analysis.note')}
            <span className="text-iris">
              {t('detail.analysis.noteEmphasis')}
            </span>
            {t('detail.analysis.noteTail')}
          </p>
          <InterpretationCard
            title={t('detail.analysis.cardTitle')}
            interpretation={analysis.data}
            loading={analysis.loading}
          />
        </div>
      )}

      {/* —— Tab 3：你和TA的关系（解读，M4）—— */}
      {tab === 'relation' && (
        <div
          role="tabpanel"
          id="person-panel-relation"
          aria-labelledby="person-tab-relation"
          className="space-y-3"
        >
          <p className="font-ui text-sm text-ink-soft">
            {t('detail.relation.note', { name: p.name })}
            <span className="text-iris">
              {t('detail.relation.noteEmphasis')}
            </span>
            {t('detail.relation.noteTail')}
          </p>
          <InterpretationCard
            title={t('detail.relation.cardTitle')}
            interpretation={analysis.data}
            loading={analysis.loading}
          />
        </div>
      )}
      {/* 复盘覆盖层（§10.6）：person 范围，①事实回放用该人跨对话发言 */}
      {reviewOpen && (
        <ReviewOverlay
          scope="person"
          id={p.id}
          title={p.name}
          onClose={() => setReviewOpen(false)}
        />
      )}
    </section>
  )
}
