/*
 * 群组粗分 —— 从 relation 文本里关键词归类，给关系网络一层「看一眼就懂」的聚类着色。
 *
 * 为什么粗分而非细分：relation 是自由文本（"老板""我妈""同事小张"），
 * 与其精确解析，不如粗粒度归三类 —— 家人 / 同事·工作 / 其他 —— 用一个
 * 与信笺协调的暖色相做描边区分。拿不准（无关键词命中）的退回 personColor，
 * 即「人即颜色」兜底，不强行塞进某一类。
 *
 * 注意：这是事实层之上的「呈现辅助」，不改变数据本身，只决定描边颜色。
 */

export type GroupKey = 'self' | 'family' | 'work' | 'other'

export interface GroupStyle {
  key: GroupKey
  /** 图例文案的 i18n key（graph 命名空间下，由组件层 t() 渲染） */
  labelKey: string
  /** 描边/标识色 —— 低反差暖色，HSL 字符串 */
  stroke: string
}

/** 家人关键词：覆盖常见称谓。 */
const FAMILY_WORDS = [
  '妈', '爸', '父', '母', '爷', '奶', '外婆', '外公', '姥',
  '哥', '姐', '弟', '妹', '儿', '女', '妻', '夫', '老婆', '老公',
  '叔', '伯', '姑', '舅', '姨', '家人', '亲戚', '表', '堂',
]

/** 同事 / 工作关键词。 */
const WORK_WORDS = [
  '同事', '老板', '上司', '领导', '下属', '客户', '合作', '同行',
  '老师', '导师', '学生', '老板娘', '助理', '经理', '总监', '工作',
]

/** 群组配色 —— 三个暖色相，饱和度/亮度收窄以贴合燕麦信笺。 */
const GROUP_STYLES: Record<GroupKey, GroupStyle> = {
  // 「我」用品牌 pine 描边，作为真相锚的延伸
  self: { key: 'self', labelKey: 'legend.self', stroke: 'var(--pine)' },
  // 家人：暖橙
  family: { key: 'family', labelKey: 'legend.family', stroke: 'hsl(28 48% 52%)' },
  // 同事·工作：暖青绿（与 pine 同温区但区分得开）
  work: { key: 'work', labelKey: 'legend.work', stroke: 'hsl(168 34% 44%)' },
  // 其他 / 拿不准：中性暖灰，让 personColor 自己说话
  other: { key: 'other', labelKey: 'legend.other', stroke: 'hsl(38 16% 58%)' },
}

/**
 * 由 relation 文本（与是否为「自己」）粗分到群组。
 * - relation === '自己' → self
 * - 命中家人词 → family
 * - 命中工作词 → work
 * - 其余（含 null / 无命中）→ other（呈现上退回 personColor）
 */
export function classifyGroup(relation: string | null): GroupKey {
  if (relation === '自己') return 'self'
  if (!relation) return 'other'
  const r = relation.trim()
  if (FAMILY_WORDS.some((w) => r.includes(w))) return 'family'
  if (WORK_WORDS.some((w) => r.includes(w))) return 'work'
  return 'other'
}

export function groupStyle(key: GroupKey): GroupStyle {
  return GROUP_STYLES[key]
}

/** 图例顺序（self 不进图例，它在画面里已足够显眼）。 */
export const LEGEND_GROUPS: GroupKey[] = ['family', 'work', 'other']
