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

import { getConversations } from '../api/client'
import { useAsync } from '../lib/useAsync'
import { PageHeader } from '../components/PageHeader'
import { WaveformMark } from '../components/WaveformMark'
import { LoadingBlock, EmptyState, ErrorState } from '../components/states'
import { Heatmap } from './today/Heatmap'
import { BeforeMeeting } from './today/BeforeMeeting'
import { ConversationCard } from './today/ConversationCard'
import { groupByDay } from './today/dateUtils'

export function TodayPage() {
  const { data, loading, error, reload } = useAsync((s) => getConversations(s), [])

  const groups = data ? groupByDay(data) : []
  const hasData = !loading && !error && data && data.length > 0

  return (
    <section>
      <PageHeader
        title="今日"
        description="今天你和谁说过话。每一段都是一份可回放、可批注的记录。"
        actions={<WaveformMark height={24} className="opacity-80" />}
      />

      {loading && <LoadingBlock label="正在加载对话…" />}

      {!loading && error && (
        <ErrorState message="暂时取不到对话列表。" onRetry={reload} />
      )}

      {!loading && !error && data && data.length === 0 && (
        <div className="space-y-4">
          {/* 空数据也保留热力图骨架，引导预期 */}
          <Heatmap conversations={[]} />
          <EmptyState
            title="还没有任何对话"
            hint="开始录音后，今天和你说过话的人会出现在这里。"
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
                    {g.label}
                  </h2>
                  <span className="font-mono text-xs text-ink-soft">
                    {g.items.length} 段
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
