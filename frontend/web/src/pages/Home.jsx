import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Home() {
  const { token } = useAuth()
  return (
    <div className="text-center space-y-8 py-12">
      <div className="text-8xl tracking-widest font-light text-gray-900 dark:text-white select-none">
        ◯-△-⬟
      </div>
      <div>
        <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-3">
          Open Identity Symbols
        </h1>
        <p className="text-lg text-gray-600 dark:text-gray-400 text-center leading-relaxed">
          A global, privacy-first identity system. Your identity is three symbols — permanently yours,
          universally unique, human-readable.
        </p>
      </div>
      <div className="flex flex-col sm:flex-row gap-3 justify-center">
        {token ? (
          <Link
            to="/dashboard"
            className="px-6 py-3 rounded-lg bg-violet-600 text-white font-medium hover:bg-violet-700"
          >
            Go to Dashboard
          </Link>
        ) : (
          <>
            <Link
              to="/register"
              className="px-6 py-3 rounded-lg bg-violet-600 text-white font-medium hover:bg-violet-700"
            >
              Get your symbol ID
            </Link>
            <Link
              to="/search"
              className="px-6 py-3 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              Search identities
            </Link>
          </>
        )}
      </div>
      <div className="grid grid-cols-3 gap-4 max-w-sm mx-auto text-sm text-gray-500">
        {[
          { icon: '🔒', text: 'Privacy-first' },
          { icon: '🌍', text: '125B+ unique IDs' },
          { icon: '🔐', text: 'TOTP secured' },
        ].map(f => (
          <div key={f.text} className="flex flex-col items-center gap-1">
            <span className="text-2xl">{f.icon}</span>
            <span>{f.text}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
