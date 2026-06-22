/*
 * 通用状态件：loading 骨架、空态、错误态。
 * 各占位页/屏级实现都靠这几个，保证「后端没起也不白屏」。
 */

export function LoadingBlock({ label = '正在加载…' }: { label?: string }) {
  return (
    <div className="space-y-3" role="status" aria-live="polite">
      <span className="sr-only">{label}</span>
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="animate-pulse rounded-card border border-line bg-card p-4"
          aria-hidden="true"
        >
          <div className="mb-2 h-3 w-1/3 rounded bg-ink/10" />
          <div className="mb-1.5 h-3 w-5/6 rounded bg-ink/10" />
          <div className="h-3 w-2/3 rounded bg-ink/10" />
        </div>
      ))}
    </div>
  )
}

export function EmptyState({
  title,
  hint,
}: {
  title: string
  hint?: string
}) {
  return (
    <div className="rounded-card border border-dashed border-line bg-card/60 px-6 py-12 text-center">
      <p className="font-record text-base text-ink">{title}</p>
      {hint && <p className="mt-1.5 font-ui text-sm text-ink-soft">{hint}</p>}
    </div>
  )
}

export function ErrorState({
  message = '加载失败，请稍后再试。',
  onRetry,
}: {
  message?: string
  onRetry?: () => void
}) {
  return (
    <div className="rounded-card border border-dashed border-line bg-card/60 px-6 py-10 text-center">
      <p className="font-ui text-sm text-ink-soft">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 font-ui text-sm font-medium text-pine hover:underline"
        >
          重试
        </button>
      )}
    </div>
  )
}
