import { useEffect, useState } from 'react'
import './App.css'

const publicNavItems = [
  { id: 'landing', label: 'Landing', href: '#/' },
  { id: 'login', label: 'Login', href: '#/login' },
  { id: 'signup', label: 'Sign Up', href: '#/signup' },
]

const appNavItems = [
  { id: 'dashboard', label: 'Dashboard', href: '#/dashboard', shortLabel: 'D' },
  { id: 'upload', label: 'Upload', href: '#/upload', shortLabel: 'U' },
  { id: 'manual', label: 'Manual', href: '#/manual', shortLabel: 'M' },
  { id: 'ai', label: 'AI', href: '#/ai', shortLabel: 'AI' },
  { id: 'analytics', label: 'Analytics', href: '#/analytics', shortLabel: 'AN' },
]

const authConfig = {
  login: {
    title: 'Log in to AI File Assistant.',
    eyebrow: 'LOGIN',
    submitLabel: 'LOG IN',
    endpoint: '/login',
    idleMessage: 'Enter your username and password to log in.',
    successFallback: 'Login successful',
    altText: 'Need a new account?',
    altHref: '#/signup',
    altLabel: 'Create one',
  },
  signup: {
    title: 'Create an AI File Assistant account.',
    eyebrow: 'SIGN UP',
    submitLabel: 'SIGN UP',
    endpoint: '/signup',
    idleMessage: 'Choose a username and password to create an account.',
    successFallback: 'Account created',
    altText: 'Already have access?',
    altHref: '#/login',
    altLabel: 'Log in',
  },
}

const appPageTitles = {
  dashboard: 'Dashboard',
  upload: 'Upload',
  manual: 'Manual',
  ai: 'AI',
  analytics: 'Analytics',
}

function getPageFromHash(hash) {
  switch (hash) {
    case '#/login':
      return 'login'
    case '#/signup':
      return 'signup'
    case '#/dashboard':
      return 'dashboard'
    case '#/upload':
      return 'upload'
    case '#/manual':
      return 'manual'
    case '#/ai':
      return 'ai'
    case '#/analytics':
      return 'analytics'
    default:
      return 'landing'
  }
}

function isAppPage(page) {
  return Object.hasOwn(appPageTitles, page)
}

function FractalCluster({ compact = false }) {
  const className = compact ? 'fractal fractal--compact' : 'fractal'

  return (
    <div className={className} aria-hidden="true">
      <div className="fractal__core" />
      <div className="fractal__ring fractal__ring--one" />
      <div className="fractal__ring fractal__ring--two" />
      <div className="fractal__ring fractal__ring--three" />
      <div className="fractal__node fractal__node--one" />
      <div className="fractal__node fractal__node--two" />
      <div className="fractal__node fractal__node--three" />
      <div className="fractal__node fractal__node--four" />
      <div className="fractal__axis fractal__axis--x" />
      <div className="fractal__axis fractal__axis--y" />
    </div>
  )
}

function UploadWidget() {
  const [files, setFiles] = useState([])
  const [isUploading, setIsUploading] = useState(false)
  const [status, setStatus] = useState({
    type: 'idle',
    message: 'Select files, then press upload.',
  })

  const handleFileChange = (event) => {
    const selectedFiles = Array.from(event.target.files || [])
    setFiles(selectedFiles)
    setStatus({
      type: 'idle',
      message: selectedFiles.length > 0 ? 'Files ready to upload.' : 'Select files, then press upload.',
    })
  }

  const handleUpload = async () => {
    if (files.length === 0) {
      setStatus({
        type: 'error',
        message: 'Select at least one file first.',
      })
      return
    }

    setIsUploading(true)
    setStatus({
      type: 'loading',
      message: 'Uploading files...',
    })

    try {
      const formData = new FormData()
      files.forEach((file) => {
        formData.append('files', file)
      })

      const response = await fetch('/embed-files', {
        method: 'POST',
        body: formData,
      })

      const payload = await response.json().catch(() => ({}))
      const message =
        payload.message ||
        payload.error ||
        `Processed ${files.length} file${files.length === 1 ? '' : 's'}.`

      if (!response.ok) {
        setStatus({ type: 'error', message })
        return
      }

      setStatus({ type: 'success', message })
    } catch {
      setStatus({
        type: 'error',
        message: 'Could not reach the backend. Make sure the Flask server is running on port 5000.',
      })
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="upload-widget">
      <label className="upload-dropzone">
        <input type="file" multiple onChange={handleFileChange} className="upload-input" />
        <span className="scan-label">Files</span>
        <h2>Select one or more files.</h2>
      </label>

      <div className="upload-preview">
        {files.length > 0 ? (
          <ul className="upload-list">
            {files.map((file) => (
              <li key={`${file.name}-${file.lastModified}`} className="upload-list__item">
                <span className="upload-list__name">{file.name}</span>
              </li>
            ))}
          </ul>
        ) : null}
      </div>

      <button
        type="button"
        className="action-button upload-action"
        onClick={handleUpload}
        disabled={isUploading}
      >
        {isUploading ? 'UPLOADING' : 'UPLOAD'}
      </button>

      <p className={`upload-status upload-status--${status.type}`} role="status" aria-live="polite">
        {status.message}
      </p>
    </div>
  )
}

function ManualWidget() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [isSearching, setIsSearching] = useState(false)
  const [status, setStatus] = useState({
    type: 'idle',
    message: 'Enter a search query and press enter.',
  })

  const handleSubmit = async (event) => {
    event.preventDefault()

    if (!query.trim()) {
      setStatus({
        type: 'error',
        message: 'Enter a search query first.',
      })
      setResults([])
      return
    }

    setIsSearching(true)
    setStatus({
      type: 'loading',
      message: 'Searching...',
    })

    try {
      const response = await fetch('/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query.trim(),
          n_results: 3,
        }),
      })

      const payload = await response.json().catch(() => ({}))
      const message = payload.message || payload.error

      if (!response.ok) {
        setStatus({
          type: 'error',
          message: message || 'Search failed.',
        })
        setResults([])
        return
      }

      const nextResults = Array.isArray(payload.results) ? payload.results : []
      setResults(nextResults)
      setStatus({
        type: 'success',
        message:
          nextResults.length > 0
            ? `Found ${nextResults.length} result${nextResults.length === 1 ? '' : 's'}.`
            : 'No results found.',
      })
    } catch {
      setStatus({
        type: 'error',
        message: 'Could not reach the backend. Make sure the Flask server is running on port 5000.',
      })
      setResults([])
    } finally {
      setIsSearching(false)
    }
  }

  return (
    <form className="manual-widget" onSubmit={handleSubmit}>
      <p className="manual-subtitle">Search for you files manually</p>

      <div className="manual-controls">
        <input
          type="text"
          className="manual-search"
          placeholder="Search files"
          aria-label="Search files manually"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <button type="submit" className="action-button manual-action" disabled={isSearching}>
          {isSearching ? 'SEARCHING' : 'Enter'}
        </button>
      </div>

      <p className={`manual-status manual-status--${status.type}`} role="status" aria-live="polite">
        {status.message}
      </p>

      {results.length > 0 ? (
        <div className="manual-results">
          {results.map((result, index) => (
            <article
              key={`${result.filename || result.source || 'result'}-${index}`}
              className="manual-result"
            >
              {result.filename ? <h2>{result.filename}</h2> : null}
              {result.source ? <p className="manual-result__meta">{result.source}</p> : null}
              {typeof result.distance === 'number' ? (
                <p className="manual-result__meta">Distance: {result.distance.toFixed(4)}</p>
              ) : null}
              {result.text ? <p className="manual-result__text">{result.text}</p> : null}
            </article>
          ))}
        </div>
      ) : null}
    </form>
  )
}

function LandingPage() {
  return (
    <div className="page page--landing">
      <section className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">AI-FILE ASSISTANT</p>
          <h1>AI File Assistant</h1>
          <p className="lede">A simple landing page for the AI File Assistant website.</p>
          <div className="logo-panel" aria-label="AI File Assistant logo">
            <div className="logo-panel__mark">AFA</div>
            <div className="logo-panel__text">
              <span>AI</span>
              <span>FILE</span>
              <span>ASSISTANT</span>
            </div>
          </div>
        </div>
        <div className="hero-visual">
          <div className="landing-card">
            <span className="scan-label">Welcome</span>
            <h2>Choose a page from the top navigation.</h2>
            <p>Use the links above to open the landing page, login page, or sign up page.</p>
          </div>
        </div>
      </section>
    </div>
  )
}

function AuthPage({ mode }) {
  const config = authConfig[mode]
  const [formData, setFormData] = useState({ username: '', password: '' })
  const [status, setStatus] = useState({ type: 'idle', message: config.idleMessage })
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleChange = (event) => {
    const { name, value } = event.target
    setFormData((current) => ({ ...current, [name]: value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()

    if (!formData.username.trim() || !formData.password) {
      setStatus({
        type: 'error',
        message: 'Username and password are required.',
      })
      return
    }

    setIsSubmitting(true)
    setStatus({
      type: 'loading',
      message: mode === 'login' ? 'Logging in...' : 'Creating account...',
    })

    try {
      const response = await fetch(config.endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: formData.username.trim(),
          password: formData.password,
        }),
      })

      const payload = await response.json().catch(() => ({}))
      const message = payload.message || payload.error || config.successFallback

      if (!response.ok) {
        setStatus({ type: 'error', message })
        return
      }

      setStatus({ type: 'success', message })
      window.location.hash = '#/dashboard'
    } catch {
      setStatus({
        type: 'error',
        message: 'Could not reach the backend. Make sure the Flask server is running on port 5000.',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="page page--auth">
      <section className="auth-shell">
        <div className="auth-intro">
          <p className="eyebrow">{config.eyebrow}</p>
          <h1>{config.title}</h1>
          <p className="lede">This page is connected to the Flask backend.</p>
          <div className="auth-note">
            <span>BACKEND</span>
            <strong>Requests are sent to {config.endpoint} using username and password.</strong>
          </div>
          <FractalCluster compact />
        </div>

        <form className="auth-card" onSubmit={handleSubmit}>
          <div className="auth-card__header">
            <span className="scan-label">Credentials</span>
            <p>{config.idleMessage}</p>
          </div>

          <div className="field-stack">
            <label className="field">
              <span>Username</span>
              <input
                name="username"
                type="text"
                autoComplete={mode === 'login' ? 'username' : 'new-password'}
                placeholder="username"
                value={formData.username}
                onChange={handleChange}
              />
            </label>

            <label className="field">
              <span>Password</span>
              <input
                name="password"
                type="password"
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                placeholder="************"
                value={formData.password}
                onChange={handleChange}
              />
            </label>
          </div>

          <button type="submit" className="action-button action-button--full" disabled={isSubmitting}>
            {isSubmitting ? 'PLEASE WAIT' : config.submitLabel}
          </button>

          <p className={`auth-status auth-status--${status.type}`} role="status" aria-live="polite">
            {status.message}
          </p>

          <p className="auth-switch">
            {config.altText} <a href={config.altHref}>{config.altLabel}</a>
          </p>
        </form>
      </section>
    </div>
  )
}

function AppPage({ page }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)

  return (
    <div className="workspace-shell">
      <aside className={isSidebarOpen ? 'sidebar is-open' : 'sidebar is-collapsed'}>
        <button
          type="button"
          className="sidebar-toggle"
          onClick={() => setIsSidebarOpen((current) => !current)}
          aria-label={isSidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          aria-expanded={isSidebarOpen}
        >
          <span />
          <span />
          <span />
        </button>

        <nav className="sidebar-nav" aria-label="Workspace navigation">
          {appNavItems.map((item) => (
            <a
              key={item.id}
              href={item.href}
              className={item.id === page ? 'sidebar-link is-active' : 'sidebar-link'}
              aria-label={item.label}
            >
              <span className="sidebar-link__icon">{item.shortLabel}</span>
              {isSidebarOpen ? <span className="sidebar-link__text">{item.label}</span> : null}
            </a>
          ))}
        </nav>
      </aside>

      <section className="workspace-page">
        <h1>{appPageTitles[page]}</h1>
        {page === 'upload' ? <UploadWidget /> : null}
        {page === 'manual' ? <ManualWidget /> : null}
      </section>
    </div>
  )
}

function App() {
  const [page, setPage] = useState(() => getPageFromHash(window.location.hash))

  useEffect(() => {
    const syncPage = () => setPage(getPageFromHash(window.location.hash))

    if (!window.location.hash) {
      window.location.hash = '#/'
    }

    syncPage()
    window.addEventListener('hashchange', syncPage)

    return () => window.removeEventListener('hashchange', syncPage)
  }, [])

  return (
    <div className="app-shell">
      {isAppPage(page) ? null : (
        <header className="topbar">
          <a className="brand" href="#/">
            <span className="brand__mark">AFA</span>
            <span className="brand__text">AI-File Assistant</span>
          </a>

          <nav className="nav-rail" aria-label="Primary navigation">
            {publicNavItems.map((item) => (
              <a
                key={item.id}
                href={item.href}
                className={item.id === page ? 'nav-rail__link is-active' : 'nav-rail__link'}
              >
                {item.label}
              </a>
            ))}
          </nav>
        </header>
      )}

      <main className={isAppPage(page) ? 'main-shell main-shell--workspace' : 'main-shell'}>
        {page === 'landing' ? <LandingPage /> : null}
        {page === 'login' ? <AuthPage key={page} mode={page} /> : null}
        {page === 'signup' ? <AuthPage key={page} mode={page} /> : null}
        {isAppPage(page) ? <AppPage key={page} page={page} /> : null}
      </main>
    </div>
  )
}

export default App
