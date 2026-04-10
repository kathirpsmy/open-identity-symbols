import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { profileApi } from '../api/client'

const LABELS = {
  display_name: 'Name', bio: 'Bio', location: 'Location',
  website: 'Website', occupation: 'Occupation',
}

export default function PublicProfile() {
  const { symbolId } = useParams()
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    profileApi.getPublic(decodeURIComponent(symbolId))
      .then(res => setProfile(res.data))
      .catch(err => {
        if (err.response?.status === 404) setNotFound(true)
      })
      .finally(() => setLoading(false))
  }, [symbolId])

  if (loading) return <div className="text-center text-gray-500 py-16">Loading…</div>

  if (notFound) {
    return (
      <div className="text-center py-16">
        <div className="text-5xl mb-4">◯-△-⬟</div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">Identity not found</h2>
        <p className="text-gray-500 mb-4">No identity matches <code className="bg-gray-100 dark:bg-gray-700 px-1 rounded">{decodeURIComponent(symbolId)}</code></p>
        <Link to="/search" className="text-violet-600 hover:underline">Search for identities</Link>
      </div>
    )
  }

  const hasData = profile && Object.keys(profile.data).length > 0

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-8 text-center">
        <div className="text-5xl font-light tracking-widest mb-3 text-gray-900 dark:text-white">
          {profile.symbol_id}
        </div>
        <div className="font-mono text-lg text-violet-600 dark:text-violet-400 mb-4">
          {profile.alias}
        </div>
        {profile.data.display_name && (
          <p className="text-xl font-medium text-gray-900 dark:text-white">{profile.data.display_name}</p>
        )}
        {profile.data.bio && (
          <p className="text-gray-600 dark:text-gray-400 mt-2 max-w-md mx-auto">{profile.data.bio}</p>
        )}
      </div>
      {hasData && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 divide-y divide-gray-100 dark:divide-gray-700">
          {Object.entries(profile.data).map(([key, value]) => (
            value && key !== 'display_name' && key !== 'bio' ? (
              <div key={key} className="flex items-center justify-between px-5 py-3">
                <span className="text-sm text-gray-500">{LABELS[key] || key}</span>
                {key === 'website' ? (
                  <a
                    href={value.startsWith('http') ? value : `https://${value}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-violet-600 hover:underline"
                  >
                    {value}
                  </a>
                ) : (
                  <span className="text-sm text-gray-900 dark:text-white">{value}</span>
                )}
              </div>
            ) : null
          ))}
        </div>
      )}
      {!hasData && (
        <p className="text-center text-sm text-gray-400">No public information shared.</p>
      )}
    </div>
  )
}
