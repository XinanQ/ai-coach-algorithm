import { authenticateDemoUser } from '../auth/permissions'

export async function login(username, password) {
  const user = authenticateDemoUser(username, password)

  if (!user) {
    throw new Error('账号或密码错误')
  }

  return user
}

export async function getMe() {
  const storedUser = localStorage.getItem('currentUser')
  return storedUser ? JSON.parse(storedUser) : null
}

export async function logout() {
  return true
}
