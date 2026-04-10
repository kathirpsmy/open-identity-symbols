import { useState } from 'react'
import { Link } from 'react-router-dom'
import { searchApi } from '../api/client'

function ResultCard({ result }) {
  const hasPublicData = Object.keys(result.data).length > 0
  return (
    <Link
      to={`/u/${encodeURIComponent(result.symbol_id)}`}
      className="block bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 hover:border-violet-300 dark:hover:border-violet-600 transition-colors"
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-xl">{result.symbol_id}</span>
        <span className="font-mono text-sm text-violet-600 dark:text-violet-400">{result.alias}</span>
      </div>
      {hasPublicData && (
        <div className="text-sm text-gray-600 dark:text-gray-400">
          {result.data.display_name && <p className="font-medium">{result.data.display_name}</p>}
          {result.data.bio && <p className="truncate">{result.data.bio}</p>}
        </div>
      )}
    </Link>
  )
}

export default function Search() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSearch(e) {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setError('')
    try {
      const res = await searchApi.search(query.trim())
      setResults(res.data)
    } catch (err) {
      setError('Search failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Search</h1>
        <p className="text-gray-500 mt-1">Find identities by symbol ID or alias.</p>
      </div>
      <form onSubmit={handleSearch} className="flex gap-2">
        <input
          type="search"
          value={query}
          onChange={e => setQuery(e.target.value)}
          className="flex-1 px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
          placeholder="Search symbol ID or alias…"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="px-5 py-2.5 rounded-lg bg-violet-600 text-white font-medium hover:bg-violet-700 disabled:opacity-50"
        >
          {loading ? '…' : 'Search'}
        </button>
      </form>
      {error && <p className="text-red-500 text-sm">{error}</p>}
      {results !== null && (
        results.length === 0
          ? <p className="text-center text-gray-500 py-8">No identities found for "{query}"</p>
          : <div className="space-y-3">
              <p className="text-sm text-gray-500">{results.length} result{results.length !== 1 ? 's' : ''}</p>
              {results.map(r => <ResultCard key={r.symbol_id} result={r} />)}
            </div>
      )}
    </div>
  )
}
