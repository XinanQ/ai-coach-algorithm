import { decompositionPlans, indicators } from '../data/mockData'
import { getProjectRelation, isOrgInScope } from '../auth/orgScope'
import { mockResolve } from './request'

const tempProjectsKey = 'tempProjects'

function getLocalTempProjects() {
  try {
    return JSON.parse(localStorage.getItem(tempProjectsKey) || '[]')
  } catch {
    localStorage.removeItem(tempProjectsKey)
    return []
  }
}

function setLocalTempProjects(projects) {
  localStorage.setItem(tempProjectsKey, JSON.stringify(projects))
}

async function getTempProjects() {
  try {
    const response = await fetch('/api/temp/projects')
    if (!response.ok) throw new Error('Cannot read temp projects')
    const payload = await response.json()
    setLocalTempProjects(payload.projects || [])
    return payload.projects || []
  } catch {
    localStorage.removeItem(tempProjectsKey)
    return []
  }
}

function mergeProjects(baseProjects, tempProjects) {
  const byId = new Map(baseProjects.map((project) => [project.id, project]))
  tempProjects.forEach((project) => byId.set(project.id, { ...project, isTemp: true }))
  return [...byId.values()]
}

function canDecomposeProject(project, user) {
  const assignedToOrg = decompositionPlans.some(
    (plan) => plan.projectId === project.id && plan.currentOrgId === user.orgId
  )
  const createdByCurrentOrg = project.ownerOrgId === user.orgId

  return assignedToOrg || createdByCurrentOrg
}

// export function getProjects(user) {
//   if (!user) {
//     return mockResolve(projects)
//   }
//
//   return getTempProjects().then((tempProjects) => {
//     const allProjects = mergeProjects(projects, tempProjects)
//
//     const visibleProjects = allProjects
//       .filter((project) => {
//         const createdInScope = isOrgInScope(project.ownerOrgId, user.orgId)
//         const assignedToOrg = decompositionPlans.some(
//           (plan) => plan.projectId === project.id && plan.currentOrgId === user.orgId
//         )
//         return createdInScope || assignedToOrg
//       })
//       .map((project) => ({
//         ...project,
//         canConfigureIndicators: project.ownerOrgId === user.orgId,
//         canDecompose: canDecomposeProject(project, user),
//         canDelete: Boolean(project.isTemp && project.ownerOrgId === user.orgId),
//         canCreateProject: ['总行', '省行', '市行', '支行'].includes(user.level),
//         relation: getProjectRelation(project, user)
//       }))
//
//     return visibleProjects
//   })
// }

export async function getProjects(user) {
  const response = await fetch('/api/admin/projects')

  if (!response.ok) {
    throw new Error('获取项目列表失败')
  }

  const data = await response.json()

  return data.map((project) => ({
    ...project,
    relation: project.relation || project.distributionStatus || '待分解',
    canConfigureIndicators: true,
    canDecompose: true,
    canDelete: false,
    canCreateProject: user
        ? ['总行', '省行', '市行', '支行'].includes(user.level)
        : false
  }))
}

// export function getProject(projectId) {
//   return getTempProjects().then((tempProjects) => {
//     const allProjects = mergeProjects(projects, tempProjects)
//     return allProjects.find((project) => project.id === projectId) || allProjects[0]
//   })
// }

export async function getProject(projectId) {
  const response = await fetch(`/api/admin/projects/${projectId}`)

  if (!response.ok) {
    throw new Error('获取项目详情失败')
  }

  return await response.json()
}

export function getProjectIndicators(projectId) {
  return mockResolve(indicators.filter((indicator) => indicator.projectId === projectId))
}

// export async function createProject(project, user, attachmentFile = null) {
//   const payload = {
//     ...project,
//     id: project.id || `${user.orgId}-${Date.now()}`,
//     owner: user.organization,
//     ownerLevel: user.level,
//     ownerOrgId: user.orgId,
//     distributionStatus: '未下发',
//     createdAt: new Date().toISOString().slice(0, 10)
//   }
//
//   try {
//     const response = await fetch('/api/temp/projects', {
//       method: 'POST',
//       headers: { 'Content-Type': 'application/json' },
//       body: JSON.stringify(payload)
//     })
//
//     if (!response.ok) throw new Error('Cannot save temp project')
//     const result = await response.json()
//     setLocalTempProjects(result.projects || [])
//
//     if (attachmentFile) {
//       const formData = new FormData()
//       formData.append('file', attachmentFile)
//
//       const uploadResponse = await fetch(`/api/temp/projects?id=${encodeURIComponent(payload.id)}`, {
//         method: 'PUT',
//         body: formData
//       })
//
//       if (!uploadResponse.ok) {
//         console.warn('附件上传失败，但项目已创建成功。')
//       } else {
//         const uploadResult = await uploadResponse.json()
//         setLocalTempProjects(uploadResult.projects || [])
//         return uploadResult
//       }
//     }
//
//     return result
//   } catch {
//     throw new Error('开发服务器临时存储不可用，请确认 npm run dev 正在运行。')
//   }
// }
export async function createProject(project, user) {
  const response = await fetch('/api/admin/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...project,
      ownerOrgId: user?.orgId
    })
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`创建项目失败：${errorText}`)
  }

  return await response.json()
}

export async function deleteProject(projectId) {
  const response = await fetch(`/api/temp/projects?id=${encodeURIComponent(projectId)}`, {
    method: 'DELETE'
  })

  if (!response.ok) throw new Error('删除临时项目失败。')

  const result = await response.json()
  setLocalTempProjects(result.projects || [])
  return result
}

// const projectStatusTextMap = {
//   DRAFT: '草稿',
//   PLANNED: '未开始',
//   ACTIVE: '进行中',
//   PAUSED: '已暂停',
//   COMPLETED: '已结束',
//   CANCELLED: '已取消'
// }
//
// function normalizeProject(project) {
//   return {
//     ...project,
//     id: String(project.id),
//     backendId: project.id,
//     reportDeadline: project.reportDeadline
//         ? project.reportDeadline.slice(0, 5)
//         : '',
//     statusCode: project.status,
//     status: projectStatusTextMap[project.status] || project.status,
//     createdAt: project.createdAt
//         ? project.createdAt.slice(0, 10)
//         : ''
//   }
// }