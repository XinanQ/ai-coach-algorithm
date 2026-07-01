import { indicators } from '../data/mockData'
import { mockResolve, request } from './request'
import { createProjectIndicator, getLocalProjects } from './projects'

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

const PROJECT_INDICATOR_TYPE = { 结果指标: 'RESULT', 过程指标: 'PROCESS' }

// 指标库搜索：优先复用库里已有指标（供项目配置的下拉选择）
export async function getIndicatorLibrary(keyword = '') {
  const qs = new URLSearchParams({ page: '0', size: '200', enabled: 'true' })
  if (keyword) qs.set('keyword', keyword)
  const page = await request(`/api/admin/indicators?${qs.toString()}`)
  const list = page?.content || (Array.isArray(page) ? page : [])
  return list.map((item) => ({
    id: item.id,
    name: item.name,
    unit: item.unit || '',
    code: item.code
  }))
}

// 从指标库删除该指标（后端不拦"已被项目引用"，调用方需二次确认并处理报错）
export async function deleteLibraryIndicator(id) {
  return await request(`/api/admin/indicators/${id}`, { method: 'DELETE' })
}

// 搜不到时新建入库，返回带 id 的库指标（code 自动生成，保证唯一）
export async function createLibraryIndicator({ name, unit } = {}) {
  const code = `AUTO_${Date.now()}${Math.floor(Math.random() * 1000)}`
  const saved = await createIndicator({
    name,
    code,
    unit: unit || '',
    enabled: true
  })
  return { id: saved.id, name: saved.name, unit: saved.unit || unit || '', code: saved.code }
}

// 把项目配置里选/建好的库指标真正挂接到项目（后端持久化），并本地镜像一份
export async function saveProjectIndicators(projectId, cards) {
  const results = []
  cards.forEach((card, index) => {
    if (!card.indicatorId) return
    const payload = {
      indicatorId: card.indicatorId,
      unit: card.unit || '',
      ratio: Number(card.weight || 0) / 100,
      pointsStandard: Number(card.pointRule || 0),
      pointsUnit: card.unit ? `分/${card.unit}` : '分',
      bigOrderThreshold: card.bigOrderEnabled ? Number(card.bigOrderThreshold || 0) : null,
      marketingStarQuota: Number(card.talentCount || 0),
      indicatorType: PROJECT_INDICATOR_TYPE[card.indicatorType] || 'RESULT',
      targetValue: Number(card.targetValue || 0),
      sortOrder: index + 1
    }
    results.push(createProjectIndicator(projectId, payload))
  })
  const saved = await Promise.all(results)
  // 兼容项目详情/指标页的本地读取（getIndicators 优先读 localStorage）
  localStorage.setItem(indicatorsKey(projectId), JSON.stringify(cards))
  return saved
}

export async function createIndicator(payload) {
  return await request('/api/admin/indicators', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export async function updateIndicator(id, payload) {
  return await request(`/api/admin/indicators/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload)
  })
}

export function getAllIndicators() {
  return mockResolve(indicators)
}
