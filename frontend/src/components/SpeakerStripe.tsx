/*
 * SpeakerStripe —— 转写行首的细色条。
 * 用「人即颜色」给每个说话人一道竖向色条，眼睛顺着色条就能扫出谁在说话，
 * 不必读名字。与 Avatar 同源同色。
 */

import { personColor } from '../lib/personColor'

export interface SpeakerStripeProps {
  /** 颜色 key：人物 id 或说话人标签（如 'A'/'B'），未归属时用 label 也能稳定出色 */
  colorKey: string | number
  /** 高度跟随父容器，宽度可调（px），默认 3 */
  width?: number
  className?: string
  title?: string
}

export function SpeakerStripe({
  colorKey,
  width = 3,
  className = '',
  title,
}: SpeakerStripeProps) {
  const { block } = personColor(colorKey)
  return (
    <span
      aria-hidden="true"
      title={title}
      style={{ width, backgroundColor: block }}
      className={`block shrink-0 self-stretch rounded-full ${className}`}
    />
  )
}
