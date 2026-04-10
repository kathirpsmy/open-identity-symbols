import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { authApi } from '../api/client'
import { useAuth } from '../context/AuthContext'

export default function Register() {
  const navigate = useNavigate()
  const { login, setPendingEmail } = useAuth()

  const [step, setStep] = useState('form') // 'form' | 'totp'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [totpQr, setTotpQr] = useState('')
  const [totpSecret, setTotpSecret] = useState('')
  const [totpCode, setTotpCode] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleRegister(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await authApi.register(email, password)
      setTotpQr(res.data.totp_qr)
      setTotpSecret(res.data.totp_secret)
      setPendingEmail(email)
      setStep('totp')
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  async function handleConfirmTotp(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await authApi.confirmTotp(email, totpCode)
      login(res.data.access_token)
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid TOTP code')
    } finally {
      setLoading(false)
    }
  }

  if (step === 'totp') {
    return (
      <div className="max-w-md mx-auto">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-8">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Set up 2FA</h1>
          <p className="text-sm text-gray-500 mb-6">
            Scan this QR code with Google Authenticator, Authy, or any TOTP app.
          </p>
          <div className="flex justify-center mb-4">
            <img src={totpQr} alt="TOTP QR Code" className="w-48 h-48 border rounded" />
          </div>
          <details className="mb-6">
            <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
              Can't scan? Enter key manually
            </summary>
            <p className="mt-2 font-mono text-xs bg-gray-100 dark:bg-gray-700 rounded p-2 break-all select-all">
              {totpSecret}
            </p>
          </details>
          <form onSubmit={handleConfirmTotp} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                6-digit code from app
              </label>
              <input
                type="text"
                inputMode="numeric"
                maxLength={6}
                value={totpCode}
                onChange={e => setTotpCode(e.target.value.replace(/\D/g, ''))}
                className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-xl tracking-widest text-center focus:outline-none focus:ring-2 focus:ring-violet-500"
                placeholder="000000"
                required
              />
            </div>
            {error && <p className="text-red-500 text-sm">{error}</p>}
            <button
              type="submit"
              disabled={loading || totpCode.length !== 6}
              className="w-full py-2.5 rounded-lg bg-violet-600 text-white font-medium hover:bg-violet-700 disabled:opacity-50"
            >
              {loading ? 'Verifying…' : 'Confirm & Continue'}
            </button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-md mx-auto">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Create account</h1>
        <p className="text-sm text-gray-500 mb-6">
          Get your unique symbol identity — forever free.
        </p>
        <form onSubmit={handleRegister} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
              placeholder="you@example.com"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
              placeholder="Min 8 chars, 1 uppercase, 1 digit"
              required
            />
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-lg bg-violet-600 text-white font-medium hover:bg-violet-700 disabled:opacity-50"
          >
            {loading ? 'Registering…' : 'Create account'}
          </button>
        </form>
        <p className="text-sm text-center text-gray-500 mt-4">
          Already have an account?{' '}
          <Link to="/login" className="text-violet-600 hover:underline">Log in</Link>
        </p>
      </div>
    </div>
  )
}
