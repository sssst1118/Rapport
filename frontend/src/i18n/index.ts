/*
 * i18n 初始化（react-i18next）—— 开源项目要双语才不寂寞。
 *
 * 设计：
 *   - 按页拆命名空间（common 公共 chrome + 各页一个 ns），便于多人/多 agent
 *     并行翻译、各管各的 JSON、互不打架；新增语言只加 locales/<lang>/*.json。
 *   - 默认跟随浏览器语言，认不出回退英文（与 README 英文优先一致，最大化触达）；
 *     用户切换后记进 localStorage（键 rapport-lang），下次自动沿用。
 *   - 字体零改动：font-record 字族栈本就 霞鹜文楷(中)+Literata(拉丁)，英文自动落 Literata。
 */

import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

import enCommon from './locales/en/common.json'
import zhCommon from './locales/zh/common.json'
import enToday from './locales/en/today.json'
import zhToday from './locales/zh/today.json'
import enConversation from './locales/en/conversation.json'
import zhConversation from './locales/zh/conversation.json'
import enPeople from './locales/en/people.json'
import zhPeople from './locales/zh/people.json'
import enGraph from './locales/en/graph.json'
import zhGraph from './locales/zh/graph.json'
import enReview from './locales/en/review.json'
import zhReview from './locales/zh/review.json'

/** 全部命名空间（新增页面区时在此登记）。 */
export const NAMESPACES = [
  'common',
  'today',
  'conversation',
  'people',
  'graph',
  'review',
] as const

/** 支持的语言。新增语言：加一套 locales/<lang>/*.json 并在此登记。 */
export const SUPPORTED_LANGS = ['en', 'zh'] as const
export type Lang = (typeof SUPPORTED_LANGS)[number]

const resources = {
  en: {
    common: enCommon,
    today: enToday,
    conversation: enConversation,
    people: enPeople,
    graph: enGraph,
    review: enReview,
  },
  zh: {
    common: zhCommon,
    today: zhToday,
    conversation: zhConversation,
    people: zhPeople,
    graph: zhGraph,
    review: zhReview,
  },
}

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'en',
    supportedLngs: SUPPORTED_LANGS as unknown as string[],
    // 只按主语言匹配（zh-CN / zh-TW 都归 zh）。
    load: 'languageOnly',
    ns: NAMESPACES as unknown as string[],
    defaultNS: 'common',
    interpolation: { escapeValue: false }, // React 已自带 XSS 转义
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: 'rapport-lang',
      caches: ['localStorage'],
    },
  })

export default i18n
