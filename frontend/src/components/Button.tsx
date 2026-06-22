/*
 * Button —— 界面体（chrome）按钮。三个 variant：
 *   primary   —— pine 实心，主操作（事实锚同色）
 *   secondary —— 描边，次操作
 *   ghost     —— 无边，低强度操作
 * 刻意安静、退到后面，让信笺与旁批是主角。
 */

import type { ButtonHTMLAttributes } from 'react'

type Variant = 'primary' | 'secondary' | 'ghost'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
}

const VARIANT: Record<Variant, string> = {
  primary: 'bg-pine text-paper hover:opacity-90',
  secondary: 'border border-line bg-card text-ink hover:border-ink-soft',
  ghost: 'text-ink-soft hover:bg-ink/5 hover:text-ink',
}

export function Button({
  variant = 'secondary',
  className = '',
  type = 'button',
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center gap-1.5 rounded-sm px-3.5 py-2 font-ui text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${VARIANT[variant]} ${className}`}
      {...rest}
    />
  )
}
