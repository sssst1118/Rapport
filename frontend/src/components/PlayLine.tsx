/*
 * PlayLine —— 行内的轻量「🔊 跳播这一句」按钮。
 *
 * 与 WaveformPlayer 的区别：这里不画波形、不创建 wavesurfer 实例，
 * 只用一个轻量 HTMLAudioElement 播某句的区间（start_ms ~ end_ms）。
 * 适合密集铺在每一行转写前。点一下就从该句起点开始播，播到句尾自动停。
 *
 * 音频源走 client.audioUrl(conversationId)（支持 Range，浏览器只取需要的片段）。
 */

import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

export interface PlayLineProps {
  /** 音频地址，一般来自 client.audioUrl(conversationId) */
  src: string
  startMs: number
  endMs: number
  className?: string
  /** 无障碍标签，默认「播放这一句」 */
  label?: string
}

export function PlayLine({
  src,
  startMs,
  endMs,
  className = '',
  label,
}: PlayLineProps) {
  const { t } = useTranslation('common')
  const resolvedLabel = label ?? t('audio.playLine')
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [playing, setPlaying] = useState(false)

  useEffect(() => {
    const audio = new Audio(src)
    audio.preload = 'none'
    audioRef.current = audio

    const onTime = () => {
      if (audio.currentTime * 1000 >= endMs) {
        audio.pause()
      }
    }
    const onPlay = () => setPlaying(true)
    const onPause = () => setPlaying(false)
    const onEnded = () => setPlaying(false)

    audio.addEventListener('timeupdate', onTime)
    audio.addEventListener('play', onPlay)
    audio.addEventListener('pause', onPause)
    audio.addEventListener('ended', onEnded)

    return () => {
      audio.pause()
      audio.removeEventListener('timeupdate', onTime)
      audio.removeEventListener('play', onPlay)
      audio.removeEventListener('pause', onPause)
      audio.removeEventListener('ended', onEnded)
      audioRef.current = null
    }
  }, [src, endMs])

  function toggle() {
    const audio = audioRef.current
    if (!audio) return
    if (!audio.paused) {
      audio.pause()
      return
    }
    // 从这一句的起点开始
    audio.currentTime = startMs / 1000
    void audio.play().catch(() => setPlaying(false))
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={resolvedLabel}
      aria-pressed={playing}
      title={resolvedLabel}
      className={`inline-grid size-7 place-items-center rounded-full text-pine transition-colors hover:bg-pine/10 ${className}`}
    >
      {playing ? <StopGlyph /> : <SpeakerGlyph />}
    </button>
  )
}

function SpeakerGlyph() {
  // 🔊 扬声器图标，pine 色
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M7.3 2.1 4.2 4.6H2.2c-.44 0-.8.36-.8.8v3.2c0 .44.36.8.8.8h2l3.1 2.5c.43.34 1.07.04 1.07-.51V2.62c0-.55-.64-.85-1.07-.52z" />
      <path
        d="M10.6 5.2c.7.66 1.13 1.6 1.13 2.8s-.43 2.14-1.13 2.8M12.3 3.4c1.2 1.06 1.95 2.7 1.95 4.6s-.75 3.54-1.95 4.6"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
      />
    </svg>
  )
}

function StopGlyph() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <rect x="4" y="4" width="8" height="8" rx="1.5" />
    </svg>
  )
}
