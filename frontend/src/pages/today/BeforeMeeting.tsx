/*
 * 「见面前」提示位 —— 克制的一条小入口（§10.1 可选）。
 *
 * 常驻采集之外的另一半：在见面前快速回看「这个人上次聊了什么」。
 * 这里不铺张内容，只放一句说明 + 通往人物页的入口，保持首页聚焦在「今天」。
 */

import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

export function BeforeMeeting() {
  const { t } = useTranslation('today')
  return (
    <Link
      to="/people"
      className="group flex items-center justify-between gap-3 rounded-card border border-dashed border-line bg-card/40 px-4 py-3 transition-colors hover:border-pine-soft hover:bg-card/70"
    >
      <div className="min-w-0">
        <p className="font-ui text-sm font-medium text-ink">{t('beforeMeeting.title')}</p>
        <p className="mt-0.5 font-ui text-xs text-ink-soft">
          {t('beforeMeeting.hint')}
        </p>
      </div>
      <span
        className="shrink-0 font-ui text-sm text-pine transition-transform group-hover:translate-x-0.5"
        aria-hidden="true"
      >
        {t('beforeMeeting.cta')}
      </span>
    </Link>
  )
}
