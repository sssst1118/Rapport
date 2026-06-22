/*
 * LanguageSwitcher —— 中 / EN 一键切换，常驻顶栏。
 * 切换即 i18n.changeLanguage（自动写 localStorage，下次沿用）。安静、低调，不抢戏。
 */

import { useTranslation } from 'react-i18next'
import { SUPPORTED_LANGS, type Lang } from '../i18n'

const LABEL: Record<Lang, string> = { zh: '中', en: 'EN' }

export function LanguageSwitcher() {
  const { i18n, t } = useTranslation('common')
  const current: Lang = i18n.resolvedLanguage === 'zh' ? 'zh' : 'en'

  return (
    <div
      role="group"
      aria-label={t('lang.label')}
      className="inline-flex overflow-hidden rounded-sm border border-line font-ui text-xs"
    >
      {SUPPORTED_LANGS.map((lang) => {
        const active = lang === current
        return (
          <button
            key={lang}
            type="button"
            onClick={() => void i18n.changeLanguage(lang)}
            aria-pressed={active}
            className={`px-2 py-1 transition-colors ${
              active
                ? 'bg-pine text-paper'
                : 'text-ink-soft hover:bg-ink/5 hover:text-ink'
            }`}
          >
            {LABEL[lang]}
          </button>
        )
      })}
    </div>
  )
}
