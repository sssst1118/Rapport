/*
 * CitationChip —— 一条原话出处（事实锚）。
 *
 * 解读层的每个判断都要挂上「它依据的真话」。这个小件把一条 Citation 呈现成：
 *   说话人（person_name 优先，否则 speaker_label）+ 原话 text（记录体）+ 时间码（等宽）
 *   + 一个 🔊 回放按钮（PlayLine，跳播该句区间）。
 *
 * 视觉纪律：虽然挂在 iris 旁批里，但「原话」本身属事实，用 ink/记录体呈现，
 * 让用户一眼分清——上面的判断是 AI 的「读」，这里引的是录下来的真话。
 */

import { useTranslation } from 'react-i18next'
import type { Citation } from '../api/types'
import { audioUrl } from '../api/client'
import { PlayLine } from './PlayLine'

export interface CitationChipProps {
  citation: Citation
}

/** 毫秒 → m:ss 时间码（与转写行的时间码风格一致）。 */
function formatTimecode(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000))
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

export function CitationChip({ citation }: CitationChipProps) {
  const { t } = useTranslation('common')
  const speaker = citation.person_name ?? citation.speaker_label
  const timecode = formatTimecode(citation.start_ms)

  return (
    <li className="flex items-start gap-2 rounded-sm bg-card/60 px-2.5 py-1.5">
      {/* 🔊 跳播这一句原声 */}
      <PlayLine
        src={audioUrl(citation.conversation_id)}
        startMs={citation.start_ms}
        endMs={citation.end_ms}
        label={t('citation.replaySpeaker', { speaker })}
        className="mt-0.5 shrink-0"
      />

      <div className="min-w-0 flex-1">
        {/* 说话人 + 时间码：机器记录的精确声音，等宽次级 */}
        <div className="mb-0.5 flex items-center gap-2">
          <span className="font-ui text-xs font-medium text-ink-soft">
            {speaker}
          </span>
          <span className="font-mono text-[11px] text-ink-soft/80">
            {timecode}
          </span>
        </div>
        {/* 原话本身：事实，记录体 + ink，与上方判断的语气区分 */}
        <p className="font-record text-sm leading-snug text-ink/90">
          “{citation.text}”
        </p>
      </div>
    </li>
  )
}
