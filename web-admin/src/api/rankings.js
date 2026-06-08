import { decompositionPlans, indicators, projects, employeeRankings, outletRankings, branchRankings, cityRankings } from '../data/mockData'
import { isOrgInScope } from '../auth/orgScope'
import { mockResolve } from './request'

export function getRankingOptions(user) {
  if (!user) return mockResolve({ projects: [], indicators: [] })

  const visibleProjectIds = projects
    .filter((project) => isOrgInScope(project.ownerOrgId, user.orgId))
    .map((project) => project.id)
  const assignedProjectIds = decompositionPlans
    .filter((plan) => plan.currentOrgId === user.orgId)
    .map((plan) => plan.projectId)
  const projectIds = [...new Set([...visibleProjectIds, ...assignedProjectIds])]

  return mockResolve({
    projects: projects.filter((project) => projectIds.includes(project.id)),
    indicators: indicators.filter((indicator) => projectIds.includes(indicator.projectId))
  })
}

export function getRankings(user, level = 'employee', projectId = '', indicatorId = '') {
  if (!user) return mockResolve([])

  let rankingData = {}
  
  switch (level) {
    case 'employee':
      rankingData = employeeRankings
      break
    case 'outlet':
      rankingData = outletRankings
      break
    case 'branch':
      rankingData = branchRankings
      break
    case 'city':
      rankingData = cityRankings
      break
    default:
      rankingData = employeeRankings
  }

  let data = []
  
  if (indicatorId) {
    const targetIndicatorId = parseInt(indicatorId)
    const indicator = indicators.find(ind => ind.id === targetIndicatorId)
    if (indicator) {
      const targetProjectId = indicator.projectId
      data = rankingData[targetProjectId]?.[targetIndicatorId] || []
      if (data.length === 0) {
        console.log(`No data found for indicator ${indicatorId} in project ${targetProjectId}`)
        console.log('Available projects:', Object.keys(rankingData))
        console.log('Available indicators in project:', rankingData[targetProjectId] ? Object.keys(rankingData[targetProjectId]) : 'Project not found')
      }
    } else {
      console.log(`Indicator ${indicatorId} not found`)
      console.log('Available indicators:', indicators.map(ind => `${ind.id}: ${ind.name}`))
    }
  } else {
    data = Object.values(rankingData).flatMap(projectData => Object.values(projectData).flat())
  }

  console.log(`Loaded ${data.length} ranking rows for level ${level}, indicator ${indicatorId}`)
  return mockResolve(data)
}