/*
 * 小工具：把「机器记录」的数值格式化成人能读的时间码。
 * 这些值在 UI 里一律用记录时刻体（IBM Plex Mono）呈现。
 */

/** 毫秒 -> m:ss（时间码，行内定位某句时用）。 */
export function formatTimecode(ms: number): string {
  if (!Number.isFinite(ms) || ms < 0) ms = 0
  const totalSec = Math.floor(ms / 1000)
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

/** 毫秒区间 -> 时长 m:ss（一句话有多长）。 */
export function formatDuration(startMs: number, endMs: number): string {
  return formatTimecode(Math.max(0, endMs - startMs))
}

/** ISO 时间串 -> 本地「年月日 时:分」（对话发生在何时）。失败时原样返回。 */
export function formatDateTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
