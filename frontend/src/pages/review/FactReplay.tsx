/*
 * FactReplay —— 复盘第①步「事实回放」（产品方案 §10.6）。
 *
 * 这是复盘里唯一的「事实层」步骤：只用真数据，绝不调解读端点、绝不编内容。
 *   - scope='conversation'：getConversation(id) 取整段转写，逐句列出原话，
 *     每句配 PlayLine（src=audioUrl(id)，start_ms~end_ms）一键回放原声。
 *   - scope='person'：getPersonUtterances(id) 取该人最近若干句，跨对话作事实回放，
 *     同样可逐句跳播原声（PlayLine 的 src=audioUrl(conversation_id)）。
 *
 * 视觉=信笺（paper/card + 记录体 font-record），与解读层（iris 旁批）一眼区分。
 */

import type { ReviewScope } from '../../api/types'
import { audioUrl, getConversation, getPersonUtterances } from '../../api/client'
import { useAsync } from '../../lib/useAsync'
import { formatTimecode } from '../../lib/format'
import { PlayLine } from '../../components/PlayLine'
import { Avatar } from '../../components/Avatar'
import { LoadingBlock, EmptyState, ErrorState } from '../../components/states'

/** person 范围下，最多回放最近多少句（事实回放，避免过长）。 */
const PERSON_MAX = 12

export interface FactReplayProps {
  scope: ReviewScope
  id: number
}

export function FactReplay({ scope, id }: FactReplayProps) {
  if (scope === 'person') return <PersonFacts id={id} />
  return <ConversationFacts id={id} />
}

/* —— 通用：事实层的统一外壳（说明 + 信笺底） —— */
function FactShell({
  hint,
  children,
}: {
  hint: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 font-ui text-sm text-pine">
        <span
          aria-hidden="true"
          className="inline-block size-1.5 rounded-full bg-pine"
        />
        <span className="font-medium">事实回放</span>
        <span className="text-ink-soft">·只呈现说过的原话，可回放原声</span>
      </div>
      <p className="font-ui text-sm text-ink-soft">{hint}</p>
      {children}
    </div>
  )
}

/* —— scope='conversation'：整段转写逐句回放 —— */
function ConversationFacts({ id }: { id: number }) {
  const { data, loading, error, reload } = useAsync(
    (s) => getConversation(id, s),
    [id],
  )

  if (loading) return <LoadingBlock label="正在加载这段对话的原话…" />
  if (error || !data)
    return <ErrorState message="打不开这段对话。" onRetry={reload} />

  const src = audioUrl(data.id)

  return (
    <FactShell hint="先回到当时的原话——逐句重听，确认事实，再谈你的看法。">
      {data.utterances.length === 0 ? (
        <EmptyState title="这段对话还没有转写文字" />
      ) : (
        <ol className="space-y-1 rounded-card border border-line bg-card/60 p-2">
          {data.utterances.map((u) => (
            <li
              key={u.id}
              className="flex gap-3 rounded-sm px-2 py-2 hover:bg-card"
            >
              <div className="min-w-0 flex-1">
                <div className="mb-0.5 flex items-center gap-2">
                  <span className="font-mono text-[11px] text-ink-soft/80">
                    {u.speaker_label}
                  </span>
                  <span className="font-mono text-[11px] text-ink-soft/60">
                    {formatTimecode(u.start_ms)}
                  </span>
                  {data.has_audio && (
                    <PlayLine src={src} startMs={u.start_ms} endMs={u.end_ms} />
                  )}
                </div>
                <p className="font-record text-[15px] leading-relaxed text-ink">
                  {u.text}
                </p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </FactShell>
  )
}

/* —— scope='person'：该人最近若干句，跨对话回放 —— */
function PersonFacts({ id }: { id: number }) {
  const { data, loading, error, reload } = useAsync(
    (s) => getPersonUtterances(id, s),
    [id],
  )

  if (loading) return <LoadingBlock label="正在加载这个人最近说过的话…" />
  if (error || !data)
    return <ErrorState message="取不到这个人的发言。" onRetry={reload} />

  // 最近 N 句：按时间倒序取前 PERSON_MAX 条
  const recent = [...data]
    .sort(
      (a, b) =>
        new Date(b.started_at).getTime() - new Date(a.started_at).getTime() ||
        b.start_ms - a.start_ms,
    )
    .slice(0, PERSON_MAX)

  return (
    <FactShell hint="先回看 TA 最近说过的话——逐句重听，确认事实，再谈你的看法。">
      {recent.length === 0 ? (
        <EmptyState
          title="还没有归属到此人的发言"
          hint="在对话里把某个说话人归属到 TA 之后，这里会出现 TA 说过的话。"
        />
      ) : (
        <ol className="space-y-1 rounded-card border border-line bg-card/60 p-2">
          {recent.map((u) => (
            <li
              key={u.id}
              className="flex gap-3 rounded-sm px-2 py-2 hover:bg-card"
            >
              <Avatar person={{ id, name: u.speaker_label }} size={28} />
              <div className="min-w-0 flex-1">
                <div className="mb-0.5 flex items-center gap-2">
                  <span className="truncate font-mono text-[11px] text-ink-soft/80">
                    {u.conversation_note?.trim() || '一段对话'}
                  </span>
                  <span className="font-mono text-[11px] text-ink-soft/60">
                    {formatTimecode(u.start_ms)}
                  </span>
                  <PlayLine
                    src={audioUrl(u.conversation_id)}
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
      )}
    </FactShell>
  )
}
