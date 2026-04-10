import { useState, useEffect } from 'react'
import { profileApi } from '../api/client'

const FIELD_LABELS = {
  display_name: 'Display Name',
  bio: 'Bio',
  location: 'Location',
  website: 'Website',
  occupation: 'Occupation',
}

function FieldRow({ fieldKey, label, value, visibility, onChange, onVisibilityChange }) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</label>
        <label className="flex items-center gap-1.5 text-xs text-gray-500 cursor-pointer">
          <input
            type="checkbox"
            checked={visibility === 'public'}
            onChange={e => onVisibilityChange(fieldKey, e.target.checked ? 'public' : 'private')}
            className="rounded"
          />
          Public
        </label>
      </div>
      <input
        type="text"
        value={value}
        onChange={e => onChange(fieldKey, e.target.value)}
        className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
        placeholder={`Your ${label.toLowerCase()}`}
      />
    </div>
  )
}

export default function Profile() {
  const [data, setData] = useState({
    display_name: '', bio: '', location: '', website: '', occupation: '',
  })
  const [visibility, setVisibility] = useState({
    display_name: 'private', bio: 'private', location: 'private',
    website: 'private', occupation: 'private',
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    profileApi.getMe()
      .then(res => {
        const p = res.data
        setData({ display_name: '', bio: '', location: '', website: '', occupation: '', ...p.data })
        setVisibility({ display_name: 'private', bio: 'private', location: 'private', website: 'private', occupation: 'private', ...p.visibility })
      })
      .catch(() => setError('Failed to load profile'))
      .finally(() => setLoading(false))
  }, [])

  function handleFieldChange(key, value) {
    setData(d => ({ ...d, [key]: value }))
  }

  function handleVisibilityChange(key, value) {
    setVisibility(v => ({ ...v, [key]: value }))
  }

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    setSaved(false)
    try {
      await profileApi.updateMe(data, visibility)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save profile')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="text-center text-gray-500 py-16">Loading…</div>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Profile</h1>
        <p className="text-gray-500 mt-1">Control what others can see about you.</p>
      </div>
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center gap-2 text-xs text-gray-500 bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 mb-6">
          <span>🔒</span>
          <span>Fields marked <strong>Public</strong> appear on your public profile. Private fields are only visible to you.</span>
        </div>
        <form onSubmit={handleSave} className="space-y-4">
          {Object.entries(FIELD_LABELS).map(([key, label]) => (
            <FieldRow
              key={key}
              fieldKey={key}
              label={label}
              value={data[key] || ''}
              visibility={visibility[key] || 'private'}
              onChange={handleFieldChange}
              onVisibilityChange={handleVisibilityChange}
            />
          ))}
          {error && <p className="text-red-500 text-sm">{error}</p>}
          {saved && <p className="text-green-600 text-sm">Profile saved!</p>}
          <button
            type="submit"
            disabled={saving}
            className="w-full py-2.5 rounded-lg bg-violet-600 text-white font-medium hover:bg-violet-700 disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save profile'}
          </button>
        </form>
      </div>
    </div>
  )
}
