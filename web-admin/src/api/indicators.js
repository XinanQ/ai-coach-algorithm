import { indicators } from '../data/mockData'
import { mockResolve } from './request'
import { getLocalProjects } from './projects'

const indicatorsKey = (id) => `projectIndicators:${id}`

function getStored(projectId) {
  try {
    const raw = localStorage.getItem(indicatorsKey(projectId))
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function getIndicators(projectId) {
  // 1) 在指标配置页保存过的，以本地存储为准
  const stored = getStored(projectId)
  if (stored) return mockResolve(stored)

  // 2) 本地新建项目：用创建项目时填写的指标映射为完整格式
  const local = getLocalProjects().find((project) => project.id === projectId)
  if (local) {
    const mapped = (local.indicators || []).map((ind, index) => ({
      id: `${projectId}-${index}`,
      projectId,
      name: ind.name,
      indicatorType: '结果指标',
      valueType: '金额',
      unit: ind.unit,
      weight: ind.weight,
      pointRule: ind.amount ? Number((ind.points / ind.amount).toFixed(2)) : ind.points,
      bigOrderEnabled: false,
      bigOrderThreshold: 0,
      talentCount: 0
    }))
    return mockResolve(mapped)
  }

  // 3) mock 预置项目
  return mockResolve(indicators.filter((indicator) => indicator.projectId === projectId))
}

export function saveIndicators(projectId, list) {
  localStorage.setItem(indicatorsKey(projectId), JSON.stringify(list))
  return mockResolve({ success: true })
}

export function getAllIndicators() {
  return mockResolve(indicators)
}
