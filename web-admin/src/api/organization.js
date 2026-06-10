import { organizations } from '../data/mockData'
import { mockResolve } from './request'

export function getOrganizationTree() {
  return mockResolve(organizations)
}
