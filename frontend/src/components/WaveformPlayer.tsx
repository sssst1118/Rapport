/*
 * WaveformPlayer —— 基于 wavesurfer.js 的波形播放器，也是品牌「真相锚」的主形态。
 *
 * 能力：
 *   - 整段播放，或只播某一句的区间（startMs ~ endMs）—— wavesurfer v7 的 play(start,end) 原生支持。
 *   - 清晰的播放位指示（cursor）+ pine 配色。
 *   - 给了 startMs/endMs 时，播到 endMs 自动停（用 timeupdate 守边界），并把光标停回区间起点。
 *
 * 失败/加载态：音频拉不到（后端没起）时不报红，显示安静的占位文案，不白屏。
 */

import { useEffect, useRef, useState } from 'react'
import WaveSurfer from 'wavesurfer.js'
import { formatTimecode } from '../lib/format'

export interface WaveformPlayerProps {
  /** 音频地址，一般来自 client.audioUrl(conversationId) */
  src: string
  /** 只播某句时的区间起点（毫秒）；不给则从头播 */
  startMs?: number
  /** 只播某句时的区间终点（毫秒）；不给则播到底 */
  endMs?: number
  /** 波形高度（px），默认 64 */
  height?: number
  className?: string
}

// 读取 CSS 变量得到品牌色，保证波形与设计系统同色
function cssVar(name: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

export function WaveformPlayer({
  src,
  startMs,
  endMs,
  height = 64,
  className = '',
}: WaveformPlayerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WaveSurfer | null>(null)
  const [ready, setReady] = useState(false)
  const [error, setError] = useState(false)
  const [playing, setPlaying] = useState(false)
  const [current, setCurrent] = useState(0)
  const [duration, setDuration] = useState(0)

  // 用 ref 持有区间边界，供 timeupdate 回调读取最新值，避免闭包陈旧
  const boundsRef = useRef<{ start?: number; end?: number }>({})
  boundsRef.current = {
    start: startMs != null ? startMs / 1000 : undefined,
    end: endMs != null ? endMs / 1000 : undefined,
  }

  useEffect(() => {
    if (!containerRef.current) return
    setReady(false)
    setError(false)
    setPlaying(false)

    const pine = cssVar('--pine', '#1b5a4f')
    const pineSoft = cssVar('--pine-soft', '#5e9c90')
    const line = cssVar('--line', '#dad3c4')

    const ws = WaveSurfer.create({
      container: containerRef.current,
      height,
      waveColor: line,
      progressColor: pineSoft,
      cursorColor: pine,
      cursorWidth: 2,
      barWidth: 2,
      barGap: 2,
      barRadius: 2,
      url: src,
    })
    wsRef.current = ws

    ws.on('ready', (dur) => {
      setReady(true)
      setDuration(dur)
      // 若指定了区间，把光标先停在区间起点
      const { start } = boundsRef.current
      if (start != null) ws.setTime(start)
    })
    ws.on('play', () => setPlaying(true))
    ws.on('pause', () => setPlaying(false))
    ws.on('finish', () => setPlaying(false))
    ws.on('error', () => setError(true))
    ws.on('timeupdate', (t) => {
      setCurrent(t)
      // 守区间右边界：播过 endMs 就停回起点
      const { start, end } = boundsRef.current
      if (end != null && t >= end) {
        ws.pause()
        ws.setTime(start ?? 0)
      }
    })

    return () => {
      ws.destroy()
      wsRef.current = null
    }
    // height 变化重建；src 变化重载
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [src, height])

  function toggle() {
    const ws = wsRef.current
    if (!ws || !ready) return
    if (ws.isPlaying()) {
      ws.pause()
      return
    }
    const { start, end } = boundsRef.current
    if (start != null) {
      // 从区间起点开始；给了 end 则交给 wavesurfer 的区间播放
      ws.play(start, end)
    } else {
      ws.play()
    }
  }

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <button
        type="button"
        onClick={toggle}
        disabled={!ready || error}
        aria-label={playing ? '暂停' : '播放'}
        className="grid size-10 shrink-0 place-items-center rounded-full bg-pine text-paper transition-opacity hover:opacity-90 disabled:opacity-40"
      >
        {playing ? <PauseGlyph /> : <PlayGlyph />}
      </button>

      <div className="min-w-0 flex-1">
        <div ref={containerRef} className="w-full" style={{ minHeight: height }} />
        {!ready && !error && (
          <p className="mt-1 font-ui text-xs text-ink-soft">正在加载音频…</p>
        )}
        {error && (
          <p className="mt-1 font-ui text-xs text-ink-soft">音频暂不可用</p>
        )}
      </div>

      {/* 记录时刻体（等宽）显示播放位 / 时长 */}
      <span className="shrink-0 font-mono text-xs tabular-nums text-ink-soft">
        {formatTimecode(current * 1000)} / {formatTimecode(duration * 1000)}
      </span>
    </div>
  )
}

function PlayGlyph() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M4 3.2v9.6c0 .5.55.8.97.54l7.2-4.8a.65.65 0 0 0 0-1.08l-7.2-4.8A.65.65 0 0 0 4 3.2z" />
    </svg>
  )
}

function PauseGlyph() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <rect x="4" y="3" width="3" height="10" rx="1" />
      <rect x="9" y="3" width="3" height="10" rx="1" />
    </svg>
  )
}
