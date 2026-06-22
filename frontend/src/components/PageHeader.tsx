/*
 * PageHeader —— 各页统一的标题区：大标题（记录体）+ 一句说明（界面体）。
 * 让占位页也有一致的呼吸感与排版层级。
 */

import type { ReactNode } from 'react'

export interface PageHeaderProps {
  title: string
  description?: string
  /** 右侧操作区（按钮等） */
  actions?: ReactNode
}

export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div className="mb-6 flex items-start justify-between gap-4">
      <div className="min-w-0">
        <h1 className="font-record text-2xl font-semibold tracking-tight text-ink">
          {title}
        </h1>
        {description && (
          <p className="mt-1 font-ui text-sm text-ink-soft">{description}</p>
        )}
      </div>
      {actions && <div className="shrink-0">{actions}</div>}
    </div>
  )
}
