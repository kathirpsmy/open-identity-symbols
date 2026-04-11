import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Layout({ children }) {
  const { token, logout, isAdmin } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col">
      <nav className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-3 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 text-xl font-semibold text-gray-900 dark:text-white">
          <span className="text-2xl">◯-△-⬟</span>
          <span className="text-sm font-medium">Open Identity Symbols</span>
        </Link>
        <div className="flex items-center gap-4">
          <Link to="/search" className="text-sm text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white">
            Search
          </Link>
          {token ? (
            <>
              <Link to="/dashboard" className="text-sm text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white">
                Dashboard
              </Link>
              {isAdmin && (
                <Link to="/admin" className="text-sm text-violet-600 dark:text-violet-400 hover:text-violet-700 dark:hover:text-violet-300 font-medium">
                  Admin
                </Link>
              )}
              <button
                onClick={handleLogout}
                className="text-sm px-3 py-1.5 rounded-md bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="text-sm text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white">
                Login
              </Link>
              <Link
                to="/register"
                className="text-sm px-3 py-1.5 rounded-md bg-violet-600 text-white hover:bg-violet-700"
              >
                Register
              </Link>
            </>
          )}
        </div>
      </nav>
      <main className="flex-1 px-4 py-8 max-w-2xl mx-auto w-full">
        {children}
      </main>
      <footer className="text-center text-xs text-gray-400 py-4">
        Open Identity Symbols — privacy-first Unicode identity
      </footer>
    </div>
  )
}
