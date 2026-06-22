/*
 * Avatar —— 人的色块头像。
 * 默认渲染「首字母 + 由 personColor 派生的稳定色块」；给了 avatar 图片则用图片覆盖。
 * 色由人物 id 或名字稳定哈希得到，全应用一致 —— 这是「人即颜色」的可见落点之一。
 */

import { personColor } from '../lib/personColor'

export interface AvatarPerson {
  id?: number | null
  name: string
  /** 图片 URL；给了就覆盖色块 */
  avatar?: string | null
}

export interface AvatarProps {
  person: AvatarPerson
  /** 直径（px），默认 36 */
  size?: number
  className?: string
}

/** 取姓名的「首字」作为占位标识：中文取第 1 个字，拉丁取首字母大写。 */
function initial(name: string): string {
  const trimmed = name.trim()
  if (!trimmed) return '?'
  const first = Array.from(trimmed)[0]
  return /[a-z]/i.test(first) ? first.toUpperCase() : first
}

export function Avatar({ person, size = 36, className = '' }: AvatarProps) {
  // 颜色 key 优先用 id（最稳定），没有则退回名字
  const colorKey = person.id ?? person.name
  const { block, ink } = personColor(colorKey)

  const style: React.CSSProperties = {
    width: size,
    height: size,
    fontSize: Math.round(size * 0.42),
  }

  if (person.avatar) {
    return (
      <img
        src={person.avatar}
        alt={person.name}
        width={size}
        height={size}
        style={style}
        className={`shrink-0 rounded-full object-cover ${className}`}
      />
    )
  }

  return (
    <span
      aria-label={person.name}
      title={person.name}
      style={{ ...style, backgroundColor: block, color: ink }}
      className={`inline-flex shrink-0 select-none items-center justify-center rounded-full font-ui font-medium leading-none ${className}`}
    >
      {initial(person.name)}
    </span>
  )
}
