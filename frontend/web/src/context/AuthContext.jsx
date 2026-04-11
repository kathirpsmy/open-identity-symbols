import { createContext, useContext, useState, useEffect } from 'react'
import { authApi } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('ois_token'))
  const [pendingEmail, setPendingEmail] = useState(null) // set during registration flow
  const [isAdmin, setIsAdmin] = useState(false)

  // Fetch user info whenever we have a token so isAdmin stays current
  useEffect(() => {
    if (!token) {
      setIsAdmin(false)
      return
    }
    authApi.getMe()
      .then(res => setIsAdmin(res.data.is_admin))
      .catch(() => setIsAdmin(false))
  }, [token])

  function login(accessToken) {
    localStorage.setItem('ois_token', accessToken)
    setToken(accessToken)
  }

  function logout() {
    localStorage.removeItem('ois_token')
    setToken(null)
    setIsAdmin(false)
  }

  return (
    <AuthContext.Provider value={{ token, login, logout, pendingEmail, setPendingEmail, isAdmin }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
