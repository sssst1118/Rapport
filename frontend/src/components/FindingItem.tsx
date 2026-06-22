/*
 * FindingItem —— 一条解读：一个判断 + 它依据的原话出处。
 *
 * 结构对应「事实与解读分离」：
 *   point  = AI 的「读」（判断），用记录体 + iris 语气呈现，明确是旁批；
 *   quotes = 这条判断锚在哪些真话上（CitationChip），点 🔊 即可回放原声。
 *
 * 这样用户一眼就能核对：这条判断的依据，正是下面这几句录下来的真话。
 */

import type { Finding } from '../api/types'
import { CitationChip } from './CitationChip'

export interface FindingItemProps {
  finding: Finding
}

export function FindingItem({ finding }: FindingItemProps) {
  const { point, quotes } = finding
  const hasQuotes = quotes.length > 0

  return (
    <li className="space-y-2">
      {/* 解读判断本身（iris 语气，记录体——这是「读」，非事实） */}
      <p className="font-record text-sm leading-relaxed text-iris">{point}</p>

      {hasQuotes ? (
        <ul className="space-y-1.5">
          {quotes.map((quote) => (
            <CitationChip key={quote.utterance_id} citation={quote} />
          ))}
        </ul>
      ) : (
        // 诚实：这条判断暂时没挂上原话出处，提示而非假装有据
        <p className="font-ui text-xs text-ink-soft/80">（暂无可回放的原话出处）</p>
      )}
    </li>
  )
}
