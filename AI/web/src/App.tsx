import { useEffect, useMemo, useRef, useState } from "react"
import {
  Activity,
  ArrowUp,
  BrainCircuit,
  CircleStop,
  Clock,
  Cpu,
  Search,
  SquarePen,
  History,
  Settings2,
  Sun,
  Moon,
  X,
  Download,
  Copy,
  ChevronDown,
  Code2,
  Gauge,
  Globe,
  HardDrive,
  KeyRound,
  AlertTriangle,
  Layers,
  Link2,
  LoaderCircle,
  RefreshCw,
  SlidersHorizontal,
  Timer,
  Trash2,
  Zap,
  ImagePlus,
  Terminal,
  MousePointer2,
  ShieldCheck,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { getHealth, listModels, streamChat, type ChatMessage, type HealthResponse, type StreamChatResult } from "@/lib/api"
import { Brand } from "./components/Brand"
import { Markdown } from "./components/Markdown"
import { persistPublicSettings, stored } from "@/lib/storage"
import { cn } from "@/lib/utils"
import { useLocale } from "./i18n"

export type View = "chat" | "settings"

const message = (role: ChatMessage["role"], content: string, images?: string[]): ChatMessage => {
  let id: string
  try {
    id = crypto.randomUUID()
  } catch {
    id = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0
      return (c === "x" ? r : (r & 0x3) | 0x8).toString(16)
    })
  }
  return images?.length ? { id, role, content, images } : { id, role, content }
}

const GHOSTHAND_TOOLS = [
  { name: "app_launch", desc: "Launch Windows executable and attach session" },
  { name: "session_attach", desc: "Attach to existing window or process ID" },
  { name: "session_status", desc: "Inspect current active session health" },
  { name: "session_end", desc: "Detach and cleanup active automation session" },
  { name: "window_list", desc: "List top-level windows of target application" },
  { name: "window_focus", desc: "Bring specific window handle to foreground" },
  { name: "window_close", desc: "Close window by handle" },
  { name: "ui_observe", desc: "Hierarchical UIA control tree scan and caching" },
  { name: "ui_find", desc: "Semantic lookup by Name, AutomationId, or ControlType" },
  { name: "ui_get_properties", desc: "Inspect control patterns and bounding rect" },
  { name: "ui_click", desc: "Invoke/Toggle control pattern without moving cursor" },
  { name: "ui_type", desc: "Keyboard typing into editable element or Document" },
  { name: "ui_set_value", desc: "Direct text value setting via ValuePattern" },
  { name: "ui_keys", desc: "Send navigation or hotkey sequences (e.g. ctrl+s)" },
]

export default function App() {
  const { t, locale, setLocale, locales } = useLocale()

  const servedByEngine = typeof window !== "undefined" && window.location.port !== "5173" && window.location.protocol.startsWith("http")
  const defaultBase = servedByEngine ? `${window.location.origin}/v1` : "http://127.0.0.1:8000/v1"

  const [baseUrl, setBaseUrl] = useState(() => {
    const saved = stored(localStorage, "pocketai.baseUrl", defaultBase)
    if (servedByEngine && saved.includes(":8000/v1") && defaultBase !== saved) return defaultBase
    return saved
  })
  const [apiKey, setApiKey] = useState("")
  const [models, setModels] = useState<string[]>([])
  const [model, setModel] = useState(() => stored(localStorage, "pocketai.model", "pocket-ai-ghosthand"))
  const [temperature, setTemperature] = useState(0.2)
  const [maxTokens, setMaxTokens] = useState(4096)
  const [thinking, setThinking] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [healthError, setHealthError] = useState("")
  const [lastRun, setLastRun] = useState<StreamChatResult | null>(null)
  const [draft, setDraft] = useState("")
  const [loading, setLoading] = useState(false)
  const [tokenCount, setTokenCount] = useState(0)
  const [tokPerSec, setTokPerSec] = useState<number | null>(null)
  const [ttft, setTtft] = useState<number | null>(null)
  const [totalTokens, setTotalTokens] = useState({ prompt: 0, completion: 0 })
  const [connecting, setConnecting] = useState(false)
  const [connected, setConnected] = useState(false)
  const [view, setView] = useState<View>("chat")
  const [settingsPage, setSettingsPage] = useState<"general" | "connection" | "automation">("general")
  const [historyOpen, setHistoryOpen] = useState(false)
  const [query, setQuery] = useState("")
  const [archives, setArchives] = useState<Array<{ id: string; messages: ChatMessage[] }>>([])
  const [theme, setTheme] = useState(() => stored(localStorage, "pocketai.theme", "dark"))
  const [copied, setCopied] = useState<string | null>(null)
  const draftRef = useRef<HTMLTextAreaElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const [pending, setPending] = useState<string[]>([])
  const historyDialog = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try {
      localStorage.setItem("pocketai.theme", theme)
    } catch {}
  }, [theme])

  useEffect(() => {
    if (historyOpen) historyDialog.current?.showModal()
    else historyDialog.current?.close()
  }, [historyOpen])

  const [error, setError] = useState("")
  const autoConnected = useRef(false)
  const abortRef = useRef<AbortController | null>(null)
  const probeRef = useRef<AbortController | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    persistPublicSettings(localStorage, baseUrl, model)
  }, [baseUrl, model])

  useEffect(() => {
    setConnected(false)
    setHealth(null)
    setHealthError("")
  }, [baseUrl, apiKey])

  useEffect(() => () => {
    probeRef.current?.abort()
    abortRef.current?.abort()
  }, [])

  useEffect(() => {
    if (!connected) return
    let disposed = false
    const poll = async () => {
      if (document.visibilityState === "hidden") return
      try {
        const result = await getHealth(baseUrl, apiKey)
        if (!disposed) {
          setHealth(result)
          setHealthError("")
        }
      } catch (cause) {
        if (!disposed) setHealthError(cause instanceof Error ? cause.message : "status.runtimeUnavailable")
      }
    }
    const timer = window.setInterval(() => void poll(), 5000)
    return () => {
      disposed = true
      window.clearInterval(timer)
    }
  }, [apiKey, baseUrl, connected])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const connect = async () => {
    probeRef.current?.abort()
    const controller = new AbortController()
    probeRef.current = controller
    setConnecting(true)
    setError("")
    try {
      const found = await listModels(baseUrl, apiKey, controller.signal)
      setModels(found)
      if (found.length && !found.includes(model)) setModel(found[0])
      setConnected(true)
      try {
        setHealth(await getHealth(baseUrl, apiKey, controller.signal))
        setHealthError("")
      } catch (cause) {
        if (!controller.signal.aborted) {
          setHealth(null)
          setHealthError(cause instanceof Error ? cause.message : "status.runtimeUnavailable")
        }
      }
    } catch (cause) {
      if (controller.signal.aborted) return
      setConnected(false)
      setError(cause instanceof Error ? cause.message : "status.serverError")
    } finally {
      if (probeRef.current === controller) {
        probeRef.current = null
        setConnecting(false)
      }
    }
  }

  if (servedByEngine && !autoConnected.current && !connected) {
    autoConnected.current = true
    setTimeout(() => connect(), 0)
  }

  const attach = async (files: FileList | File[] | null) => {
    const pictures = Array.from(files || []).filter((file) => file.type.startsWith("image/"))
    if (!pictures.length) return
    const read = (file: File) =>
      new Promise<string>((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = () => resolve(String(reader.result))
        reader.onerror = reject
        reader.readAsDataURL(file)
      })
    try {
      const urls = await Promise.all(pictures.map(read))
      setPending((list) => [...list, ...urls])
    } catch {
      setError("Failed to attach image.")
    }
  }

  const canSend = !loading && (draft.trim().length > 0 || pending.length > 0)

  const send = async (explicitText?: string, priorMessages?: ChatMessage[]) => {
    const text = (explicitText ?? draft).trim()
    const images = explicitText !== undefined ? [] : pending
    if ((!text && !images.length) || loading) return

    const user = message("user", text, images)
    const baseList = priorMessages ?? messages
    const nextMessages = [...baseList, user]
    setMessages(nextMessages)

    if (explicitText === undefined) {
      setDraft("")
      setPending([])
    }
    setError("")
    setLoading(true)
    setTokenCount(0)
    setTokPerSec(null)
    setTtft(null)

    const assistant = message("assistant", "")
    setMessages((current) => [...current, assistant])

    const controller = new AbortController()
    abortRef.current = controller
    const t0 = performance.now()
    let decodeStart: number | null = null
    let count = 0

    try {
      const result = await streamChat({
        baseUrl,
        apiKey,
        model,
        messages: nextMessages,
        temperature,
        maxTokens,
        enableThinking: thinking,
        signal: controller.signal,
        onDelta: (delta: string) => {
          if (!delta) return
          count += 1
          setTokenCount(count)
          if (decodeStart === null) {
            decodeStart = performance.now()
            setTtft(decodeStart - t0)
          }
          const since = (performance.now() - decodeStart) / 1000
          if (count > 1 && since > 0.2) setTokPerSec((count - 1) / since)
          setMessages((current) =>
            current.map((item) => (item.id === assistant.id ? { ...item, content: item.content + delta } : item)),
          )
        },
      })

      const decodeElapsed = (performance.now() - (decodeStart || t0)) / 1000
      if (count > 1 && decodeElapsed > 0) setTokPerSec((count - 1) / decodeElapsed)
      if (result.usage) {
        setTotalTokens((prev) => ({
          prompt: prev.prompt + (result.usage?.prompt_tokens || 0),
          completion: prev.completion + (result.usage?.completion_tokens || 0),
        }))
      }
      setLastRun(result)
      setConnected(true)
    } catch (cause) {
      if (controller.signal.aborted) {
        setMessages((current) => current.filter((item) => item.id !== assistant.id || item.content))
      } else {
        setError(cause instanceof Error ? cause.message : "status.generationFailed")
        setMessages((current) => current.filter((item) => item.id !== assistant.id || item.content))
      }
    } finally {
      abortRef.current = null
      setLoading(false)
    }
  }

  const openSettings = (page: "general" | "connection" | "automation" = "general") => {
    setSettingsPage(page)
    setView("settings")
  }

  const clearChat = () => {
    setMessages([])
    setLastRun(null)
    setTokPerSec(null)
    setTtft(null)
    setTokenCount(0)
    setTotalTokens({ prompt: 0, completion: 0 })
    setError("")
  }

  const newChat = () => {
    if (loading) return
    if (messages.length) {
      setArchives((items) => [{ id: message("system", "").id, messages: [...messages] }, ...items])
    }
    clearChat()
    setDraft("")
    setView("chat")
    requestAnimationFrame(() => draftRef.current?.focus())
  }

  const exportChat = () => {
    const url = URL.createObjectURL(
      new Blob([JSON.stringify({ model, messages }, null, 2)], { type: "application/json" }),
    )
    const anchor = document.createElement("a")
    anchor.href = url
    anchor.download = "pocket-ai-chat.json"
    anchor.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  const copyMessage = async (item: ChatMessage) => {
    try {
      await navigator.clipboard.writeText(item.content)
      setCopied(item.id)
    } catch {
      setError(t("ui.copyError"))
    }
  }

  const restoreArchive = (entry: { id: string; messages: ChatMessage[] }) => {
    if (loading) return
    setArchives((items) => [...items.filter((item) => item.id !== entry.id)])
    setMessages(entry.messages)
    setView("chat")
    setHistoryOpen(false)
    setLastRun(null)
    setError("")
    setDraft("")
  }

  const empty = messages.length === 0

  const connectionControls = (
    <fieldset disabled={loading}>
      <section className="side-section">
        <div className="section-title">
          <Link2 className="size-3.5" /> {t("sidebar.connection")}
        </div>
        <label>
          {t("sidebar.endpoint")}
          <Input id="endpoint" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} />
        </label>
        <label>
          {t("sidebar.apiKey")}
          <div className="relative">
            <KeyRound className="field-icon" />
            <Input
              id="api-key"
              className="pl-9"
              type="password"
              value={apiKey}
              placeholder={t("sidebar.apiKeyPlaceholder")}
              onChange={(event) => setApiKey(event.target.value)}
            />
          </div>
          <span className="field-help">{t("sidebar.apiKeyHelp")}</span>
        </label>
        <Button type="button" variant="secondary" onClick={connect} disabled={connecting}>
          {connecting ? <LoaderCircle className="size-4 animate-spin" /> : <RefreshCw className="size-4" />}
          {t("sidebar.probe")}
        </Button>
        <div className={cn("connection-state", connected && "connected")} aria-live="polite">
          <span />
          {connected ? "Pocket AI Backend Connected" : t("status.notConnected")}
        </div>
      </section>
    </fieldset>
  )

  const automationControls = (
    <section className="side-section">
      <div className="section-title">
        <ShieldCheck className="size-3.5" /> GhostHand Automation Engine
      </div>
      <div className="space-y-4 text-sm text-[var(--muted-foreground)]">
        <div className="p-3 rounded-lg border border-[var(--border)] bg-[var(--card)]">
          <div className="flex items-center gap-2 font-medium text-[var(--foreground)] mb-1">
            <MousePointer2 className="size-4 text-cyan-400" /> Untouched Mouse Cursor
          </div>
          <p className="text-xs">Direct Microsoft UI Automation (UIA3) via FlaUI. No coordinates or pixel matching.</p>
        </div>
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-[var(--foreground)] mb-2">
            Loaded Tools ({GHOSTHAND_TOOLS.length})
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {GHOSTHAND_TOOLS.map((tool) => (
              <div key={tool.name} className="p-2 rounded border border-[var(--border)] text-xs">
                <code className="text-purple-400 font-semibold">{tool.name}</code>
                <div className="text-[11px] text-[var(--muted-foreground)]">{tool.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )

  const metrics = (
    <div className="live-metrics" aria-live="polite">
      {loading && tokenCount > 0 ? (
        <Badge className="badge-live">
          <Zap className="size-3 flash" /> {t("topbar.tokens", { n: tokenCount })}
        </Badge>
      ) : null}
      {tokPerSec != null ? (
        <Badge className={cn("badge-speed", loading && "badge-live")}>
          <Gauge className="size-3" /> {t("topbar.tokPerSec", { n: tokPerSec.toFixed(1) })}
        </Badge>
      ) : null}
      {!loading && ttft != null ? (
        <Badge>
          <Timer className="size-3" /> TTFT {(ttft / 1000).toFixed(1)}s
        </Badge>
      ) : null}
      {!loading && lastRun?.usage ? (
        <Badge>
          <Layers className="size-3" /> {lastRun.usage.prompt_tokens}→{lastRun.usage.completion_tokens}
        </Badge>
      ) : null}
      {!loading && lastRun?.finishReason === "length" ? (
        <Badge className="badge-warn" title={t("topbar.truncatedHelp")}>
          <AlertTriangle className="size-3" /> {t("topbar.truncated")}
        </Badge>
      ) : null}
    </div>
  )

  return (
    <div className="app-shell redesigned">
      <aside className="rail" aria-label={t("ui.sidebar")}>
        <button className="rail-brand" title="Pocket AI" onClick={() => setView("chat")}>
          <Brand />
        </button>
        <button className="rail-button" aria-label={t("ui.newChat")} title={t("ui.newChat")} onClick={newChat} disabled={loading}>
          <SquarePen />
        </button>
        <button
          className="rail-button"
          aria-label={t("ui.search")}
          title={t("ui.search")}
          onClick={() => {
            setQuery("")
            setHistoryOpen(true)
          }}
        >
          <Search />
        </button>
        <button
          className="rail-button"
          aria-label={t("ui.history")}
          title={t("ui.history")}
          onClick={() => {
            setQuery("")
            setHistoryOpen(true)
          }}
        >
          <History />
        </button>
        <div className="rail-bottom">
          <button
            className={cn("rail-button", view === "settings" && "active")}
            aria-label={t("ui.settings")}
            title={t("ui.settings")}
            onClick={() => openSettings()}
          >
            <Settings2 />
          </button>
          <button
            className="rail-button"
            aria-label={t("ui.theme")}
            title={t("ui.theme")}
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          >
            {theme === "dark" ? <Sun /> : <Moon />}
          </button>
        </div>
      </aside>

      <main className="workspace">
        <header className="workspace-topbar">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm tracking-tight text-[var(--foreground)]">Pocket AI</span>
            <Badge className="text-[11px] font-normal border-purple-500/30 text-purple-400">
              GhostHand Agent
            </Badge>
          </div>
          <div className="workspace-actions">
            <button className={cn("connection-state", connected && "connected")} onClick={() => openSettings("connection")}>
              <span />
              {connected ? "Agent Online" : t("status.notConnected")}
            </button>
            {view === "chat" && (
              <>
                <button className="icon-action" aria-label={t("ui.export")} title={t("ui.export")} disabled={empty} onClick={exportChat}>
                  <Download />
                </button>
                <button
                  className="icon-action"
                  aria-label={t("topbar.clear")}
                  title={t("topbar.clear")}
                  disabled={empty || loading}
                  onClick={clearChat}
                >
                  <Trash2 />
                </button>
              </>
            )}
          </div>
        </header>

        {view === "settings" ? (
          <section className="settings-page">
            <header className="page-heading">
              <span>POCKET AI</span>
              <h1>{t("ui.settings")}</h1>
              <p>Configure backend connection, agent parameters, and view GhostHand tools.</p>
            </header>
            <nav className="settings-tabs" aria-label={t("ui.settings")}>
              {(["general", "connection", "automation"] as const).map((id) => (
                <button
                  key={id}
                  aria-current={settingsPage === id ? "page" : undefined}
                  onClick={() => setSettingsPage(id)}
                >
                  {id === "automation" ? "Automation" : t(`ui.${id}`)}
                </button>
              ))}
            </nav>
            {error && <div className="error-banner" role="alert">{t(error)}</div>}
            <div className="settings-content">
              {settingsPage === "general" && (
                <section className="settings-card">
                  <h2>{t("ui.appearance")}</h2>
                  <div className="theme-choices">
                    {["dark", "light"].map((value) => (
                      <button
                        key={value}
                        className={`theme-choice ${value}`}
                        aria-pressed={theme === value}
                        onClick={() => setTheme(value)}
                      >
                        <span />
                        <b>{t(`ui.${value}`)}</b>
                      </button>
                    ))}
                  </div>
                  <label className="language-field">
                    <Globe />
                    {t("ui.language")}
                    <select value={locale} onChange={(e) => setLocale(e.target.value)}>
                      {locales.map((l) => (
                        <option key={l.code} value={l.code}>
                          {l.label}
                        </option>
                      ))}
                    </select>
                  </label>
                </section>
              )}
              {settingsPage === "connection" && <section className="settings-card">{connectionControls}</section>}
              {settingsPage === "automation" && <section className="settings-card">{automationControls}</section>}
            </div>
          </section>
        ) : (
          <section className={cn("chat-view", empty && "empty")}>
            {empty ? (
              <div className="welcome-brand">
                <Brand word />
                <p className="mt-3 text-sm text-[var(--muted-foreground)] max-w-md text-center">
                  Semantic Windows Desktop Automation Agent powered by Qwen, FlaUI, and UIA3.
                </p>
              </div>
            ) : (
              <div className="conversation" role="log" aria-label={t("nav.chat")}>
                <div className="message-list">
                  {messages.map((item, index) => (
                    <article key={item.id} className={cn("message", item.role)}>
                      {item.role !== "user" && (
                        <div className="assistant-brand">
                          <Brand />
                          <span className="font-semibold text-xs tracking-wide">Pocket AI</span>
                        </div>
                      )}
                      {item.images?.length ? (
                        <div className="message-images">
                          {item.images.map((url, at) => (
                            <img key={at} src={url} alt={t("ui.attachedImage", { n: at + 1 })} />
                          ))}
                        </div>
                      ) : null}
                      <div className="message-body">
                        {item.content ? (
                          item.role === "assistant" ? (
                            <Markdown text={item.content} />
                          ) : (
                            item.content
                          )
                        ) : (
                          <span className="typing" aria-label={t("ui.generating")}>
                            <i />
                            <i />
                            <i />
                          </span>
                        )}
                      </div>
                      {item.role === "assistant" && item.content && (
                        <div className="message-actions">
                          <button
                            className="icon-action"
                            aria-label={t("ui.copy")}
                            title={t("ui.copy")}
                            onClick={() => void copyMessage(item)}
                          >
                            <Copy />
                          </button>
                          {copied === item.id && <span role="status">{t("ui.copied")}</span>}
                          {index === messages.length - 1 && !loading && (
                            <button
                              className="icon-action"
                              aria-label={t("ui.regenerate")}
                              title={t("ui.regenerate")}
                              onClick={() => {
                                const userIndex = messages
                                  .map((m, i) => (m.role === "user" && i < index ? i : -1))
                                  .reduce((a, b) => Math.max(a, b), -1)
                                if (userIndex >= 0) void send(messages[userIndex].content, messages.slice(0, userIndex))
                              }}
                            >
                              <RefreshCw />
                            </button>
                          )}
                        </div>
                      )}
                    </article>
                  ))}
                  <div ref={bottomRef} />
                </div>
              </div>
            )}

            <div className="composer-wrap">
              {metrics}
              {error && <div className="error-banner" role="alert">{t(error)}</div>}
              <form
                className="composer"
                onSubmit={(e) => {
                  e.preventDefault()
                  void send()
                }}
                onDragOver={(e) => {
                  if (e.dataTransfer.types.includes("Files")) e.preventDefault()
                }}
                onDrop={(e) => {
                  if (e.dataTransfer.files.length) {
                    e.preventDefault()
                    void attach(e.dataTransfer.files)
                  }
                }}
              >
                {pending.length > 0 && (
                  <div className="composer-attachments">
                    {pending.map((url, at) => (
                      <span key={at} className="attachment">
                        <img src={url} alt={t("ui.attachedImage", { n: at + 1 })} />
                        <button
                          type="button"
                          aria-label={t("ui.removeImage")}
                          title={t("ui.removeImage")}
                          onClick={() => setPending((list) => list.filter((_, index) => index !== at))}
                        >
                          <X />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
                <Textarea
                  ref={draftRef}
                  id="draft"
                  aria-label={t("chat.placeholder")}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  placeholder={t("chat.placeholder")}
                  onPaste={(event) => {
                    const files = Array.from(event.clipboardData.files || [])
                    if (files.length) {
                      event.preventDefault()
                      void attach(files)
                    }
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
                      event.preventDefault()
                      void send()
                    }
                  }}
                />
                <div className="composer-foot">
                  <input
                    ref={fileRef}
                    type="file"
                    accept="image/*"
                    multiple
                    hidden
                    onChange={(e) => {
                      void attach(e.target.files)
                      e.target.value = ""
                    }}
                  />
                  <button
                    type="button"
                    className="attach-chip"
                    aria-label={t("ui.attachImage")}
                    title={t("ui.attachImage")}
                    onClick={() => fileRef.current?.click()}
                  >
                    <ImagePlus />
                  </button>
                  <button
                    type="button"
                    className="reasoning-chip"
                    aria-pressed={thinking}
                    onClick={() => setThinking((value) => !value)}
                  >
                    <BrainCircuit />
                    {t("sidebar.reasoning")}
                  </button>
                  {loading ? (
                    <button
                      type="button"
                      className="send-button"
                      aria-label={t("chat.stop")}
                      onClick={() => abortRef.current?.abort()}
                    >
                      <CircleStop />
                    </button>
                  ) : (
                    <button type="submit" className="send-button" aria-label={t("chat.send")} disabled={!canSend}>
                      <ArrowUp />
                    </button>
                  )}
                </div>
              </form>

              {empty && (
                <div className="suggestions">
                  {[
                    { text: "Open Notepad and type a Python script", Icon: Terminal, label: "Notepad Automation" },
                    { text: "Open Calculator and find the sum of 20 and 74", Icon: Code2, label: "Calculator Math" },
                    { text: "List open windows and inspect active desktop session", Icon: Search, label: "Inspect Windows" },
                  ].map(({ text, Icon, label }) => (
                    <button
                      key={label}
                      onClick={() => {
                        setDraft(text)
                        draftRef.current?.focus()
                      }}
                    >
                      <Icon />
                      <span>{label}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </section>
        )}
      </main>

      <dialog
        ref={historyDialog}
        className="history-dialog"
        onCancel={() => setHistoryOpen(false)}
        onClose={() => setHistoryOpen(false)}
        onClick={(e) => {
          if (e.target === e.currentTarget) {
            const r = e.currentTarget.getBoundingClientRect()
            if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) {
              setHistoryOpen(false)
            }
          }
        }}
      >
        <header>
          <h2>{t("ui.history")}</h2>
          <button className="icon-action" aria-label={t("ui.close")} onClick={() => setHistoryOpen(false)}>
            <X />
          </button>
        </header>
        <label className="history-search">
          <Search />
          <input
            aria-label={t("ui.search")}
            placeholder={t("ui.search")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <div className="history-results">
          {archives
            .filter((entry) => entry.messages.some((m) => m.content.toLocaleLowerCase().includes(query.toLocaleLowerCase())))
            .map((entry) => (
              <button key={entry.id} disabled={loading} onClick={() => restoreArchive(entry)}>
                <History />
                <span>
                  {entry.messages.find((m) => m.role === "user")?.content.slice(0, 85)}
                  <small>{t("ui.archived")}</small>
                </span>
              </button>
            ))}
          <p>{t("ui.historyMemory")}</p>
        </div>
      </dialog>
    </div>
  )
}
