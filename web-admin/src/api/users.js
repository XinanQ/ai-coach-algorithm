import { users } from '../data/mockData'
import { isOrgInScope } from '../auth/orgScope'
import { mockResolve } from './request'

export function getUsers(user) {
  if (!user) return mockResolve([])
  return mockResolve(users.filter((item) => isOrgInScope(item.orgId, user.orgId)))
}
