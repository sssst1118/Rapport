/*
 * 对话卡 —— 今日视图的主体单元：「这段话，你和谁说的」。
 *
 * 信息层级（事实优先）：
 *   参与者头像 + 名字（人即颜色）→ note 标题（记录体）→ 时间 / 句数 / 音频在场。
 * 交互：整卡点进 /conversations/:id；参与者头像独立点进 /people/:id。
 * 为避免 <a> 嵌套 <a>，用「拉伸链接」：标题层是覆盖全卡的链接，
 *   头像链接浮在更高层级、各自可点，互不吞没。
 *
 * 特例（demo #4）：participants 为空 = 说话人尚未映射到人 ——
 *   不假装、不留白，明确提示「说话人待确认」，引导点进去认人。
 */

import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import type { ConversationListItem } from '../../api/types'
import { Avatar } from '../../components/Avatar'
import { formatClock } from './dateUtils'

interface ConversationCardProps {
  conversation: ConversationListItem
  /** 是否属于「今天」组 —— 今天的卡更醒目（实底 + pine 描边） */
  emphasized?: boolean
}

export function ConversationCard({ conversation: c, emphasized }: ConversationCardProps) {
  const { t, i18n } = useTranslation('today')
  const pending = c.participants.length === 0
  const shown = c.participants.slice(0, 4)
  const overflow = c.participants.length - shown.length
  // 名字之间的分隔符随语言而变（中文顿号 / 英文逗号），避免英文里出现「、」
  const nameSep = i18n.language.startsWith('zh') ? '、' : ', '
  const names = c.participants.map((p) => p.name).slice(0, 2).join(nameSep)

  return (
    <div
      className={[
        'group relative rounded-card border p-4 transition-colors',
        emphasized
          ? 'border-pine-soft bg-card shadow-[0_1px_0_var(--line)] hover:border-pine'
          : 'border-line bg-card hover:border-pine-soft',
      ].join(' ')}
    >
      {/* 顶部一行：参与者（左） + 时间·句数（右） */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          {pending ? (
            <span className="inline-flex h-[26px] items-center gap-1.5 rounded-full border border-dashed border-line px-2 font-ui text-xs text-ink-soft">
              {t('card.pending')}
            </span>
          ) : (
            <>
              {/* 头像叠放：负边距营造「并排叠放」 */}
              <div className="flex shrink-0 items-center -space-x-2">
                {shown.map((p) => (
                  // relative z-10 让头像链接浮在拉伸链接之上，可独立点击
                  <Link
                    key={p.id}
                    to={`/people/${p.id}`}
                    title={t('card.viewPerson', { name: p.name })}
                    className="relative z-10 rounded-full ring-2 ring-card transition-transform hover:scale-110"
                  >
                    <Avatar person={p} size={26} />
                  </Link>
                ))}
                {overflow > 0 && (
                  <span className="relative z-10 inline-flex h-[26px] w-[26px] items-center justify-center rounded-full bg-paper font-mono text-[10px] text-ink-soft ring-2 ring-card">
                    +{overflow}
                  </span>
                )}
              </div>
              {/* 名字（最多两个，多了省略） */}
              <span className="truncate font-record text-sm text-ink">
                {names}
                {c.participants.length > 2 &&
                  ` ${t('card.namesOverflow', { count: c.participants.length })}`}
              </span>
            </>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-2 pt-0.5 font-mono text-xs text-ink-soft">
          <span>{formatClock(c.started_at, i18n.language)}</span>
          <span aria-hidden="true">·</span>
          <span>{t('card.utteranceCount', { count: c.utterance_count })}</span>
        </div>
      </div>

      {/* note 标题（记录体）—— 这也是覆盖全卡的「拉伸链接」 */}
      <Link
        to={`/conversations/${c.id}`}
        className="mt-2.5 block font-record text-base text-ink before:absolute before:inset-0 before:content-['']"
      >
        <span className="relative">
          {c.note?.trim() || (pending ? t('card.pendingNote') : t('card.noNote'))}
        </span>
      </Link>

      {/* 底部一行：音频在场标记 / 待确认引导 */}
      <div className="mt-2 flex items-center gap-3">
        {c.has_audio && (
          <span className="inline-flex items-center gap-1 font-ui text-xs text-pine">
            {/* 音频在场的小标记：一段定格波形 */}
            <svg width="14" height="10" viewBox="0 0 14 10" aria-hidden="true">
              {[3, 7, 9, 5, 8, 4].map((h, i) => (
                <rect
                  key={i}
                  x={i * 2.4}
                  y={(10 - h) / 2}
                  width="1.4"
                  height={h}
                  rx="0.7"
                  fill="var(--pine)"
                />
              ))}
            </svg>
            {t('card.hasAudio')}
          </span>
        )}
        {pending && (
          <span className="relative z-10 font-ui text-xs text-ink-soft">
            {t('card.pendingHint')}
          </span>
        )}
      </div>
    </div>
  )
}
