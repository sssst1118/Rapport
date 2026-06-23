/*
 * 设置 /settings —— 界面内配置语言模型，落 config.json（M5.5 Task 3）。
 *
 * 让用户不碰环境变量、不编辑文件，点几下就配好 Ollama / Anthropic。只读写配置，
 * 不触发任何 LLM 调用。沿用《记录与旁批》设计系统：暖燕麦底 + 松绿主操作 +
 * 记录体/界面体排版，与其它页同气质，刻意安静、退到后面。
 *
 * 数据流：useAsync(getSettings) 拉当前有效设置回显 → 本地表单态编辑 →
 * saveSettings 持久化 → 成功提示。API key 绝不回显明文：has_api_key 为真时输入框
 * 只给「已设置（留空则不修改）」占位，留空保存即不动已存 key。
 * env_overrides 里的项给「被环境变量覆盖」提示（改这里不生效）。
 */

import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { LlmProvider } from '../api/types'
import { getSettings, saveSettings } from '../api/client'
import { useAsync } from '../lib/useAsync'
import { PageHeader } from '../components/PageHeader'
import { Button } from '../components/Button'
import { LoadingBlock, ErrorState } from '../components/states'

const PROVIDERS: LlmProvider[] = ['none', 'ollama', 'anthropic']

/** 表单输入统一样式（与 PersonCreateDialog 等现有表单一致）。 */
const FIELD =
  'w-full rounded-sm border border-line bg-paper px-3 py-2 font-ui text-sm text-ink outline-none placeholder:text-ink-soft/50 focus:border-pine-soft'

/** 某项被环境变量覆盖时的小字提示。 */
function EnvOverrideNote({ show }: { show: boolean }) {
  const { t } = useTranslation('settings')
  if (!show) return null
  return (
    <p className="mt-1.5 font-ui text-xs text-iris" role="note">
      {t('envOverride')}
    </p>
  )
}

export function SettingsPage() {
  const { t } = useTranslation('settings')
  const { data, loading, error, reload } = useAsync((s) => getSettings(s), [])

  // 本地表单态：随加载结果初始化（key 永远不回显，输入框只收新值）。
  const [provider, setProvider] = useState<LlmProvider>('none')
  const [model, setModel] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [saved, setSaved] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  // 拉到设置后把有效值灌进表单（仅在数据到达/刷新时）。
  useEffect(() => {
    if (!data) return
    setProvider(data.llm_provider)
    setModel(data.llm_model)
    setApiKey('')
  }, [data])

  const overrides = data?.env_overrides ?? []
  const providerOverridden = overrides.includes('llm_provider')
  const modelOverridden = overrides.includes('llm_model')
  const keyOverridden = overrides.includes('anthropic_api_key')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setSaved(false)
    setSaveError(null)
    try {
      await saveSettings({
        llm_provider: provider,
        llm_model: model.trim(),
        // 留空 = 不改已存 key；非空才提交（后端同样把空串视作不覆盖）。
        ...(apiKey.trim() ? { anthropic_api_key: apiKey.trim() } : {}),
      })
      setSaved(true)
      setApiKey('')
      reload() // 重新拉取，刷新 has_api_key / env_overrides 回显
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : t('failed'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section>
      <PageHeader title={t('title')} description={t('description')} />

      {loading && <LoadingBlock label={t('title')} />}
      {!loading && error && (
        <ErrorState message={t('loadError')} onRetry={reload} />
      )}

      {!loading && !error && data && (
        <form
          onSubmit={handleSubmit}
          className="max-w-xl rounded-card border border-line bg-card p-5 sm:p-6"
        >
          <h2 className="font-record text-lg font-semibold text-ink">
            {t('section.llm')}
          </h2>
          <p className="mb-5 mt-1 font-ui text-sm text-ink-soft">
            {t('section.llmHint')}
          </p>

          {/* 后端下拉 */}
          <label className="mb-4 block">
            <span className="mb-1 block font-ui text-xs font-medium text-ink-soft">
              {t('provider.label')}
            </span>
            <select
              value={provider}
              onChange={(e) => {
                setProvider(e.target.value as LlmProvider)
                setSaved(false)
              }}
              className={FIELD}
            >
              {PROVIDERS.map((p) => (
                <option key={p} value={p}>
                  {t(`provider.${p}`)}
                </option>
              ))}
            </select>
            <EnvOverrideNote show={providerOverridden} />
          </label>

          {/* 模型名（none 时无意义，禁用并留灰提示） */}
          <label className="mb-4 block">
            <span className="mb-1 block font-ui text-xs font-medium text-ink-soft">
              {t('model.label')}
            </span>
            <input
              value={model}
              onChange={(e) => {
                setModel(e.target.value)
                setSaved(false)
              }}
              disabled={provider === 'none'}
              placeholder={t(`model.placeholder.${provider}`)}
              className={`${FIELD} font-record disabled:opacity-50`}
            />
            <EnvOverrideNote show={modelOverridden} />
          </label>

          {/* API Key：仅 Anthropic 显示；已设则占位提示「留空不改」，绝不回显明文 */}
          {provider === 'anthropic' && (
            <label className="mb-4 block">
              <span className="mb-1 block font-ui text-xs font-medium text-ink-soft">
                {t('apiKey.label')}
              </span>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => {
                  setApiKey(e.target.value)
                  setSaved(false)
                }}
                autoComplete="off"
                placeholder={
                  data.has_api_key
                    ? t('apiKey.placeholderSet')
                    : t('apiKey.placeholderUnset')
                }
                className={FIELD}
              />
              <p className="mt-1.5 font-ui text-xs text-ink-soft/80">
                {t('apiKey.hint')}
              </p>
              <EnvOverrideNote show={keyOverridden} />
            </label>
          )}

          {/* 保存 + 反馈 */}
          <div className="mt-5 flex items-center gap-3">
            <Button type="submit" variant="primary" disabled={submitting}>
              {submitting ? t('saving') : t('save')}
            </Button>
            {saved && (
              <span
                className="font-ui text-sm text-pine"
                role="status"
                aria-live="polite"
              >
                {t('saved')}
              </span>
            )}
            {saveError && (
              <span className="font-ui text-sm text-live" role="alert">
                {saveError}
              </span>
            )}
          </div>
        </form>
      )}
    </section>
  )
}
