import { useState, useEffect } from 'react'
import { profileApi, authApi } from '../api/client'

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

function TOTPResetSection() {
  const [phase, setPhase] = useState('idle') // idle | confirm | scanning | done
  const [qr, setQr] = useState(null)
  const [secret, setSecret] = useState(null)
  const [email, setEmail] = useState(null)
  const [confirmCode, setConfirmCode] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  async function handleReset() {
    setError('')
    setBusy(true)
    try {
      const res = await authApi.resetTotp()
      setQr(res.data.totp_qr)
      setSecret(res.data.totp_secret)
      // Retrieve email for confirm-totp call
      const me = await authApi.getMe()
      setEmail(me.data.email)
      setPhase('scanning')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to reset TOTP')
    } finally {
      setBusy(false)
    }
  }

  async function handleConfirm(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const res = await authApi.confirmTotp(email, confirmCode)
      // Update stored token with the fresh one
      localStorage.setItem('ois_token', res.data.access_token)
      setPhase('done')
      setSuccess('TOTP re-confirmed. Your authenticator app is updated.')
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid code — try again')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">Two-Factor Authentication</h2>
      <p className="text-sm text-gray-500 mb-4">
        Reset your TOTP if you've lost access to your authenticator app or switched devices.
        Your current session stays active, but you'll need to re-confirm before logging in again.
      </p>

      {phase === 'idle' && (
        <>
          {error && <p className="text-red-500 text-sm mb-3">{error}</p>}
          <button
            onClick={() => setPhase('confirm')}
            className="px-4 py-2 rounded-lg border border-red-300 text-red-600 text-sm hover:bg-red-50 dark:hover:bg-red-900/20"
          >
            Reset TOTP secret
          </button>
        </>
      )}

      {phase === 'confirm' && (
        <div className="space-y-3">
          <p className="text-sm text-amber-600 dark:text-amber-400 font-medium">
            This will invalidate your current authenticator entry. Continue?
          </p>
          <div className="flex gap-3">
            <button
              onClick={handleReset}
              disabled={busy}
              className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm hover:bg-red-700 disabled:opacity-50"
            >
              {busy ? 'Resetting…' : 'Yes, reset TOTP'}
            </button>
            <button
              onClick={() => setPhase('idle')}
              className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-sm text-gray-700 dark:text-gray-300"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {phase === 'scanning' && (
        <div className="space-y-4">
          <p className="text-sm text-gray-700 dark:text-gray-300">
            Scan this new QR code in your authenticator app, then enter the 6-digit code below to confirm.
          </p>
          {qr && <img src={qr} alt="New TOTP QR code" className="w-48 h-48 rounded-lg border border-gray-200 dark:border-gray-600" />}
          <details className="text-xs text-gray-500">
            <summary className="cursor-pointer">Can't scan? Enter secret manually</summary>
            <code className="block mt-1 break-all font-mono bg-gray-50 dark:bg-gray-700 rounded p-2">{secret}</code>
          </details>
          <form onSubmit={handleConfirm} className="space-y-3">
            <input
              type="text"
              inputMode="numeric"
              maxLength={6}
              placeholder="6-digit code"
              value={confirmCode}
              onChange={e => setConfirmCode(e.target.value.replace(/\D/g, ''))}
              className="w-40 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
            />
            {error && <p className="text-red-500 text-sm">{error}</p>}
            <button
              type="submit"
              disabled={busy || confirmCode.length !== 6}
              className="px-4 py-2 rounded-lg bg-violet-600 text-white text-sm hover:bg-violet-700 disabled:opacity-50"
            >
              {busy ? 'Confirming…' : 'Confirm new TOTP'}
            </button>
          </form>
        </div>
      )}

      {phase === 'done' && (
        <p className="text-green-600 dark:text-green-400 text-sm">{success}</p>
      )}
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
      <TOTPResetSection />
    </div>
  )
}
