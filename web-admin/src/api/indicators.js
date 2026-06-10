import { indicators } from '../data/mockData'
import { mockResolve } from './request'

export function getIndicators(projectId) {
  return mockResolve(indicators.filter((indicator) => indicator.projectId === projectId))
}

export function getAllIndicators() {
  return mockResolve(indicators)
}
