import { useState, useEffect } from 'react'
import { adminApi } from '../api/client'

function StatCard({ label, value }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 flex flex-col gap-1">
      <span className="text-xs text-gray-500 uppercase tracking-wide">{label}</span>
      <span className="text-3xl font-bold text-gray-900 dark:text-white">{value ?? '—'}</span>
    </div>
  )
}

export default function Admin() {
  const [analytics, setAnalytics] = useState(null)
  const [users, setUsers] = useState([])
  const [loadingAnalytics, setLoadingAnalytics] = useState(true)
  const [loadingUsers, setLoadingUsers] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    adminApi.getAnalytics()
      .then(res => setAnalytics(res.data))
      .catch(() => setError('Failed to load analytics'))
      .finally(() => setLoadingAnalytics(false))

    adminApi.listUsers()
      .then(res => setUsers(res.data))
      .catch(() => setError(e => e || 'Failed to load users'))
      .finally(() => setLoadingUsers(false))
  }, [])

  async function toggleActive(user) {
    try {
      const res = user.is_active
        ? await adminApi.deactivateUser(user.id)
        : await adminApi.activateUser(user.id)
      setUsers(prev => prev.map(u => u.id === user.id ? res.data : u))
    } catch (err) {
      setError(err.response?.data?.detail || 'Action failed')
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Admin</h1>
        <p className="text-gray-500 mt-1">Platform overview and user management</p>
      </div>

      {error && (
        <div className="text-red-600 text-sm bg-red-50 dark:bg-red-900/20 rounded-lg px-4 py-3">
          {error}
        </div>
      )}

      {/* Analytics */}
      <section>
        <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">Analytics</h2>
        {loadingAnalytics ? (
          <p className="text-gray-400 text-sm">Loading…</p>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <StatCard label="Total Users" value={analytics?.total_users} />
            <StatCard label="Active Users" value={analytics?.active_users} />
            <StatCard label="Inactive Users" value={analytics?.inactive_users} />
            <StatCard label="Admin Users" value={analytics?.admin_users} />
            <StatCard label="Identities" value={analytics?.total_identities} />
            <StatCard label="New (7 days)" value={analytics?.new_users_last_7_days} />
          </div>
        )}
      </section>

      {/* User management */}
      <section>
        <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">Users</h2>
        {loadingUsers ? (
          <p className="text-gray-400 text-sm">Loading…</p>
        ) : (
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs text-gray-500 uppercase tracking-wide">
                <tr>
                  <th className="text-left px-4 py-3">Email</th>
                  <th className="text-left px-4 py-3">Status</th>
                  <th className="text-left px-4 py-3">Identity</th>
                  <th className="text-left px-4 py-3">Admin</th>
                  <th className="text-left px-4 py-3">Joined</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {users.map(user => (
                  <tr key={user.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                    <td className="px-4 py-3 text-gray-900 dark:text-white font-mono">{user.email}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                        user.is_active
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                          : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                      }`}>
                        {user.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {user.has_identity ? 'Yes' : '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {user.is_admin ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400">
                          Admin
                        </span>
                      ) : '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {new Date(user.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {!user.is_admin && (
                        <button
                          onClick={() => toggleActive(user)}
                          className={`text-xs px-3 py-1.5 rounded-md font-medium ${
                            user.is_active
                              ? 'border border-red-300 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20'
                              : 'border border-green-300 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20'
                          }`}
                        >
                          {user.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {users.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-400 text-sm">
                      No users found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
