export function getCurrentUser() {
  const storedUser = localStorage.getItem('currentUser')

  if (!storedUser) return null

  try {
    return JSON.parse(storedUser)
  } catch {
    localStorage.removeItem('currentUser')
    return null
  }
}

export function setCurrentUser(user) {
  localStorage.setItem('isLoggedIn', 'true')
  localStorage.setItem('currentUser', JSON.stringify(user))
}

export function clearCurrentUser() {
  localStorage.removeItem('isLoggedIn')
  localStorage.removeItem('currentUser')
  localStorage.removeItem('authToken')
}

export function isLoggedIn() {
  return localStorage.getItem('isLoggedIn') === 'true'
}
