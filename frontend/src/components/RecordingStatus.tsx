/*
 * RecordingStatus —— 常驻顶栏的录制状态指示。
 *
 * 读 GET /api/status，轮询刷新：
 *   - 录制中：呼吸的 live 红点 + 「正在录音」（暂停时显示「已暂停」）
 *   - 未录制：静默灰点 + 「未在录音」
 * 右侧给出「暂停 / 继续」与「这段别留」两个动作的 UI 壳 —— 仅样式与可点性，
 * 暂不接后端动作（后续 agent 接）。
 *
 * 失败降级：拿不到状态（后端没起）不报红，按「未在录音」呈现，避免顶栏白屏/报错。
 */

import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getStatus } from '../api/client'
import type { Status } from '../api/types'
import { Button } from './Button'

const POLL_MS = 4000

export function RecordingStatus() {
  const { t } = useTranslation('common')
  const [status, setStatus] = useState<Status | null>(null)
  const timer = useRef<number | null>(null)

  useEffect(() => {
    let alive = true
    const ctrl = new AbortController()

    async function tick() {
      try {
        const s = await getStatus(ctrl.signal)
        if (alive) setStatus(s)
      } catch {
        // 后端没起/网络错：降级为「未在录音」，不抛红
        if (alive) setStatus({ recording: false, paused: false })
      }
    }

    void tick()
    timer.current = window.setInterval(tick, POLL_MS)
    return () => {
      alive = false
      ctrl.abort()
      if (timer.current) window.clearInterval(timer.current)
    }
  }, [])

  const recording = status?.recording ?? false
  const paused = status?.paused ?? false

  // 文案
  const label = recording
    ? paused
      ? t('recording.paused')
      : t('recording.live')
    : t('recording.idle')

  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-2">
        {recording ? (
          <span
            // 录制中：live 红点，未暂停时呼吸
            style={{ backgroundColor: 'var(--live)' }}
            className={`block size-2.5 rounded-full ${paused ? '' : 'animate-live-pulse'}`}
            aria-hidden="true"
          />
        ) : (
          <span
            className="block size-2.5 rounded-full bg-ink-soft/45"
            aria-hidden="true"
          />
        )}
        <span
          className={`font-ui text-sm font-medium ${recording && !paused ? 'text-ink' : 'text-ink-soft'}`}
        >
          {label}
        </span>
      </div>

      {/* 动作壳：录制中才显示；暂不接后端动作 */}
      {recording && (
        <div className="flex items-center gap-1.5">
          <Button
            variant="ghost"
            className="px-2.5 py-1.5 text-xs"
            // TODO(后续 agent)：接 暂停/继续 录制
            onClick={() => {}}
          >
            {paused ? t('recording.resume') : t('recording.pause')}
          </Button>
          <Button
            variant="ghost"
            className="px-2.5 py-1.5 text-xs text-live hover:bg-live/10 hover:text-live"
            // TODO(后续 agent)：接 丢弃当前片段
            onClick={() => {}}
          >
            {t('recording.discard')}
          </Button>
        </div>
      )}
    </div>
  )
}
