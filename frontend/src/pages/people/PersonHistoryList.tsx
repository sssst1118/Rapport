/*
 * PersonHistoryList —— 人物详情「对话历史」Tab 的事实层主体。
 *
 * 这是真实事实层：把某人跨多段对话说过的话，按 conversation 分组，
 * 每组带对话备注 + 发生时间，并链接到对应对话页；组内每句带
 * <PlayLine> 跳播原声（start_ms ~ end_ms）。绝不掺解读，只呈现说过的话。
 */

import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import type { PersonUtterance } from '../../api/types'
import { audioUrl } from '../../api/client'
import { formatDateTime, formatTimecode } from '../../lib/format'
import { PlayLine } from '../../components/PlayLine'
import { SpeakerStripe } from '../../components/SpeakerStripe'

/** 同一段对话的发言聚成一组，保留首条的备注/时间用作组头。 */
interface ConversationGroup {
  conversationId: number
  note: string | null
  startedAt: string
  items: PersonUtterance[]
}

function groupByConversation(utterances: PersonUtterance[]): ConversationGroup[] {
  const map = new Map<number, ConversationGroup>()
  for (const u of utterances) {
    let g = map.get(u.conversation_id)
    if (!g) {
      g = {
        conversationId: u.conversation_id,
        note: u.conversation_note,
        startedAt: u.started_at,
        items: [],
      }
      map.set(u.conversation_id, g)
    }
    g.items.push(u)
  }
  // 组内按起点排序，组间按对话时间倒序（最近的对话在上）
  const groups = Array.from(map.values())
  for (const g of groups) g.items.sort((a, b) => a.start_ms - b.start_ms)
  groups.sort(
    (a, b) => new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime(),
  )
  return groups
}

export interface PersonHistoryListProps {
  /** 用于色条与头像配色的稳定 key（人物 id） */
  personId: number
  utterances: PersonUtterance[]
}

export function PersonHistoryList({
  personId,
  utterances,
}: PersonHistoryListProps) {
  const { t } = useTranslation('people')
  const groups = groupByConversation(utterances)

  return (
    <div className="space-y-6">
      {groups.map((g) => {
        const src = audioUrl(g.conversationId)
        return (
          <section
            key={g.conversationId}
            className="rounded-card border border-line bg-card/60"
          >
            {/* 组头：对话备注 + 时间 + 进入该对话 */}
            <header className="flex items-baseline justify-between gap-3 border-b border-line px-4 py-3">
              <div className="min-w-0">
                <h3 className="truncate font-record text-base text-ink">
                  {g.note?.trim() || t('historyList.untitled')}
                </h3>
                <p className="mt-0.5 font-mono text-[11px] text-ink-soft/80">
                  {formatDateTime(g.startedAt)} · {g.items.length}{' '}
                  {t('historyList.sentenceCount', { count: g.items.length })}
                </p>
              </div>
              <Link
                to={`/conversations/${g.conversationId}`}
                className="shrink-0 font-ui text-sm font-medium text-pine hover:underline"
              >
                {t('historyList.enter')}
              </Link>
            </header>

            {/* 组内：这段对话里此人说过的每一句，可跳播原声 */}
            <ol className="space-y-1 px-2 py-2">
              {g.items.map((u) => (
                <li
                  key={u.id}
                  className="flex gap-3 rounded-sm px-2 py-2 hover:bg-card"
                >
                  <SpeakerStripe colorKey={personId} title={u.speaker_label} />
                  <div className="min-w-0 flex-1">
                    <div className="mb-0.5 flex items-center gap-2">
                      <span className="font-mono text-[11px] text-ink-soft/70">
                        {formatTimecode(u.start_ms)}
                      </span>
                      <PlayLine
                        src={src}
                        startMs={u.start_ms}
                        endMs={u.end_ms}
                      />
                    </div>
                    <p className="font-record text-[15px] leading-relaxed text-ink">
                      {u.text}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </section>
        )
      })}
    </div>
  )
}
