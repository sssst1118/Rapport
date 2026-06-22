/*
 * SummaryBand —— 正文上方的「事实摘要条」。
 *
 * 这里只放**事实**（立刻可由数据算出、不需要 AI）：
 *   - 参与者：Avatar + 名字，可点进 /people/:id
 *   - 发生时间：formatDateTime
 *   - 句数：utterances.length
 *   - 时长：首句 start_ms ~ 末句 end_ms 推算（font-mono）
 *
 * 「一句话主旨 / 话题标签」是**解读**，不在这里 —— 那些走 InterpretationCard（M4）。
 * 视觉上属信笺层：card/line + 记录体，与 iris 解读卡一眼区分。
 */

import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import type { ConversationDetail } from '../../api/types'
import { Avatar } from '../../components/Avatar'
import { formatDateTime, formatTimecode } from '../../lib/format'

export interface SummaryBandProps {
  data: ConversationDetail
}

export function SummaryBand({ data }: SummaryBandProps) {
  const { t } = useTranslation('conversation')
  const us = data.utterances
  const sentenceCount = us.length

  // 时长：首句起点 ~ 末句终点（utterances 默认按时间序）
  let durationMs = 0
  if (us.length > 0) {
    const startMs = Math.min(...us.map((u) => u.start_ms))
    const endMs = Math.max(...us.map((u) => u.end_ms))
    durationMs = Math.max(0, endMs - startMs)
  }

  return (
    <div className="mb-4 rounded-card border border-line bg-card px-4 py-3">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
        {/* 参与者 */}
        <div className="flex flex-wrap items-center gap-2">
          {data.participants.length === 0 ? (
            <span className="font-ui text-sm text-ink-soft">{t('summary.noParticipants')}</span>
          ) : (
            data.participants.map((p) => (
              <Link
                key={p.id}
                to={`/people/${p.id}`}
                title={t('summary.viewPerson', { name: p.name })}
                className="inline-flex items-center gap-1.5 rounded-full py-0.5 pr-2 pl-0.5 transition-colors hover:bg-ink/5"
              >
                <Avatar person={p} size={26} />
                <span className="font-record text-sm text-ink">{p.name}</span>
              </Link>
            ))
          )}
        </div>

        {/* 事实数值：时间 · 句数 · 时长 */}
        <dl className="ml-auto flex flex-wrap items-center gap-x-5 gap-y-1 font-ui text-xs text-ink-soft">
          <div className="flex items-center gap-1.5">
            <dt>{t('summary.occurredAt')}</dt>
            <dd className="text-ink">{formatDateTime(data.started_at)}</dd>
          </div>
          <div className="flex items-center gap-1.5">
            <dt>{t('summary.sentences')}</dt>
            <dd className="font-mono text-ink">{sentenceCount}</dd>
          </div>
          <div className="flex items-center gap-1.5">
            <dt>{t('summary.duration')}</dt>
            <dd className="font-mono text-ink">{formatTimecode(durationMs)}</dd>
          </div>
        </dl>
      </div>
    </div>
  )
}
