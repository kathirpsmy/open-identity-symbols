import { createContext, useContext, useState, useEffect } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('ois_token'))
  const [pendingEmail, setPendingEmail] = useState(null) // set during registration flow

  function login(accessToken) {
    localStorage.setItem('ois_token', accessToken)
    setToken(accessToken)
  }

  function logout() {
    localStorage.removeItem('ois_token')
    setToken(null)
  }

  return (
    <AuthContext.Provider value={{ token, login, logout, pendingEmail, setPendingEmail }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
