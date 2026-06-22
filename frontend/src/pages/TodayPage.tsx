/*
 * 今日 Today —— 常驻采集的入口/首页（产品设计 §10.1）。
 *
 * 首页不是一锅音频，而是「今天你和谁说过话」：
 *   顶部一条日历热力图（最近 12 周，按当天对话数着色）→「见面前」轻量入口
 *   → 按自然日分组的对话卡（今天最前最醒目，再昨天、更早）。
 *
 * 数据：GET /api/conversations（已最近优先）。列表端点不返回逐句 ms，
 *   所以卡上只呈现 参与者 + note + 时间 + 句数 + 音频在场，不显示时长（拿不到，不编造）。
 */

import { useTranslation } from 'react-i18next'
import { getConversations } from '../api/client'
import { useAsync } from '../lib/useAsync'
import { PageHeader } from '../components/PageHeader'
import { WaveformMark } from '../components/WaveformMark'
import { LoadingBlock, EmptyState, ErrorState } from '../components/states'
import { Heatmap } from './today/Heatmap'
import { BeforeMeeting } from './today/BeforeMeeting'
import { ConversationCard } from './today/ConversationCard'
import { groupByDay, relativeDayLabel } from './today/dateUtils'

export function TodayPage() {
  const { t, i18n } = useTranslation('today')
  const { data, loading, error, reload } = useAsync((s) => getConversations(s), [])

  const groups = data ? groupByDay(data) : []
  const hasData = !loading && !error && data && data.length > 0

  return (
    <section>
      <PageHeader
        title={t('header.title')}
        description={t('header.description')}
        actions={<WaveformMark height={24} className="opacity-80" />}
      />

      {loading && <LoadingBlock label={t('loading')} />}

      {!loading && error && (
        <ErrorState message={t('error')} onRetry={reload} />
      )}

      {!loading && !error && data && data.length === 0 && (
        <div className="space-y-4">
          {/* 空数据也保留热力图骨架，引导预期 */}
          <Heatmap conversations={[]} />
          <EmptyState
            title={t('empty.title')}
            hint={t('empty.hint')}
          />
        </div>
      )}

      {hasData && (
        <div className="space-y-6">
          {/* 顶部：日历热力图 + 「见面前」入口 */}
          <div className="space-y-3">
            <Heatmap conversations={data} />
            <BeforeMeeting />
          </div>

          {/* 按天分组的对话卡 */}
          <div className="space-y-7">
            {groups.map((g) => (
              <div key={g.key}>
                <div className="mb-2.5 flex items-baseline gap-2">
                  <h2
                    className={[
                      'font-record tracking-tight',
                      g.isToday
                        ? 'text-lg font-semibold text-ink'
                        : 'text-base text-ink-soft',
                    ].join(' ')}
                  >
                    {relativeDayLabel(g.relative, t, i18n.language)}
                  </h2>
                  <span className="font-mono text-xs text-ink-soft">
                    {t('group.count', { count: g.items.length })}
                  </span>
                  {g.isToday && (
                    <span className="ml-0.5 inline-block h-1.5 w-1.5 rounded-full bg-pine" aria-hidden="true" />
                  )}
                </div>

                <ul className="space-y-3">
                  {g.items.map((c) => (
                    <li key={c.id}>
                      <ConversationCard conversation={c} emphasized={g.isToday} />
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
