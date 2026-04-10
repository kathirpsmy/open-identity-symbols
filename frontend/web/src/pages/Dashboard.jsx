import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { identityApi } from '../api/client'

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)

  async function copy() {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <button
      onClick={copy}
      className="ml-2 px-2 py-1 text-xs rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
    >
      {copied ? '✓ Copied' : 'Copy'}
    </button>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [identity, setIdentity] = useState(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    identityApi.getMe()
      .then(res => setIdentity(res.data))
      .catch(err => {
        if (err.response?.status !== 404) {
          setError('Failed to load identity')
        }
      })
      .finally(() => setLoading(false))
  }, [])

  async function generateId() {
    setGenerating(true)
    setError('')
    try {
      const res = await identityApi.generate()
      setIdentity(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate ID')
    } finally {
      setGenerating(false)
    }
  }

  if (loading) {
    return <div className="text-center text-gray-500 py-16">Loading…</div>
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
        <p className="text-gray-500 mt-1">Your symbol identity</p>
      </div>

      {!identity ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-8 text-center">
          <div className="text-6xl mb-4">◯-△-⬟</div>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            You don't have a symbol ID yet. Generate one — it's permanent and globally unique.
          </p>
          {error && <p className="text-red-500 text-sm mb-4">{error}</p>}
          <button
            onClick={generateId}
            disabled={generating}
            className="px-6 py-3 rounded-lg bg-violet-600 text-white font-medium hover:bg-violet-700 disabled:opacity-50"
          >
            {generating ? 'Generating…' : 'Generate my Symbol ID'}
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-8">
            <div className="text-5xl font-light tracking-widest text-center mb-4 text-gray-900 dark:text-white">
              {identity.symbol_id}
            </div>
            <div className="flex items-center justify-center gap-2 mb-6">
              <span className="font-mono text-lg text-violet-600 dark:text-violet-400">
                {identity.alias}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                <div className="text-xs text-gray-500 mb-1">Symbol ID</div>
                <div className="flex items-center justify-between">
                  <code className="text-sm text-gray-900 dark:text-white">{identity.symbol_id}</code>
                  <CopyButton text={identity.symbol_id} />
                </div>
              </div>
              <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                <div className="text-xs text-gray-500 mb-1">Alias</div>
                <div className="flex items-center justify-between">
                  <code className="text-sm text-gray-900 dark:text-white">{identity.alias}</code>
                  <CopyButton text={identity.alias} />
                </div>
              </div>
            </div>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => navigate('/profile')}
              className="flex-1 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 text-sm font-medium"
            >
              Edit Profile
            </button>
            <button
              onClick={() => navigate(`/u/${encodeURIComponent(identity.symbol_id)}`)}
              className="flex-1 py-2.5 rounded-lg bg-violet-600 text-white hover:bg-violet-700 text-sm font-medium"
            >
              View Public Profile
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
