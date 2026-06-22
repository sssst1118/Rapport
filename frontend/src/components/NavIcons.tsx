/*
 * 导航图标。统一 18px、线性、currentColor，安静收敛，跟界面体的气质一致。
 */

interface IconProps {
  className?: string
}

const base = {
  width: 18,
  height: 18,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.7,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
}

/** 今日：一份信笺/记录 */
export function TodayIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <path d="M6 3h9l4 4v14H6z" />
      <path d="M14 3v5h5" />
      <path d="M9 12h7M9 16h7" />
    </svg>
  )
}

/** 人物：两个人 */
export function PeopleIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <circle cx="9" cy="8" r="3" />
      <path d="M3.5 19a5.5 5.5 0 0 1 11 0" />
      <path d="M16 6a3 3 0 0 1 0 6M17 14.5a5.5 5.5 0 0 1 3.5 4.5" />
    </svg>
  )
}

/** 关系图：相连的节点 */
export function GraphIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className} aria-hidden="true">
      <circle cx="6" cy="6" r="2.4" />
      <circle cx="18" cy="7" r="2.4" />
      <circle cx="12" cy="18" r="2.4" />
      <path d="M7.7 7.8 10.5 16M16.2 8.7 13.3 16M8.2 6.6h7.6" />
    </svg>
  )
}
