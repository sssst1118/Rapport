/*
 * useAsync —— 一个极简的异步数据 hook，给占位页/屏级实现统一的 loading/error/data 三态。
 * 自带 AbortController（卸载即取消），并提供 reload 供「重试」。
 *
 * 用法：
 *   const { data, loading, error, reload } = useAsync(
 *     (signal) => getPeople(signal), []
 *   )
 */

import { useCallback, useEffect, useState } from 'react'

export interface AsyncState<T> {
  data: T | null
  loading: boolean
  error: Error | null
  reload: () => void
}

export function useAsync<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  deps: React.DependencyList,
): AsyncState<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [nonce, setNonce] = useState(0)

  const reload = useCallback(() => setNonce((n) => n + 1), [])

  useEffect(() => {
    const ctrl = new AbortController()
    let alive = true
    setLoading(true)
    setError(null)

    fetcher(ctrl.signal)
      .then((res) => {
        if (alive) setData(res)
      })
      .catch((e: unknown) => {
        // 主动取消不算错误
        if (ctrl.signal.aborted) return
        if (alive) setError(e instanceof Error ? e : new Error(String(e)))
      })
      .finally(() => {
        if (alive) setLoading(false)
      })

    return () => {
      alive = false
      ctrl.abort()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce])

  return { data, loading, error, reload }
}
