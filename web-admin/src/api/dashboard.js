import { request } from './request'
import { projects as mockProjects, rankingRows as mockRankingRows } from '../data/mockData'

// 首页看板 ↔ GET /api/admin/dashboard/summary
// 后端按登录角色范围一次返回全部看板数据；本模块只做「取数 + 映射成页面视图模型」。
// 兼容性：保持 getDashboardSummary(user) 对外签名不变；后端不可用时回退本地 mock，保证页面不崩。

function round(value) {
  if (value == null) return 0
  const num = Number(value)
  return Number.isFinite(num) ? Math.round(num) : 0
}

function buildManagerStats(summary) {
  return [
    {
      label: '可见项目',
      value: String(summary.visibleProjectCount ?? 0),
      hint: `${summary.activeProjectCount ?? 0} 个进行中`
    },
    {
      label: '待我处理',
      value: String(summary.pendingReviewCount ?? 0),
      hint: '待审核上报',
      highlight: true
    },
    {
      label: '范围内本月积分',
      value: String(round(summary.scopePoints)),
      hint: `${summary.monthReportCount ?? 0} 笔上报`
    },
    {
      label: '平均完成度',
      value: summary.overallCompletionRate == null ? '—' : `${summary.overallCompletionRate}%`,
      hint: '进行中项目'
    }
  ]
}

function buildEmployeeStats(summary) {
  return [
    {
      label: '今日上报',
      value: summary.todayReported ? '已上报' : '未上报',
      hint: summary.todayReported ? '今日已完成' : '去每日上报',
      highlight: !summary.todayReported
    },
    {
      label: '本月积分',
      value: String(round(summary.myScore)),
      hint: '个人积分'
    },
    {
      label: '我的排名',
      value: summary.myRank == null ? '—' : `第 ${summary.myRank} 名`,
      hint: summary.myRankScope || '本月'
    },
    {
      label: '本月上报',
      value: String(summary.monthReportCount ?? 0),
      hint: '笔上报记录'
    }
  ]
}

function normalizeSummary(summary) {
  const isManager = summary.viewType === 'MANAGER'

  return {
    viewType: summary.viewType || 'EMPLOYEE',
    name: summary.name || '',
    organizationName: summary.organizationName || '',
    stats: isManager ? buildManagerStats(summary) : buildEmployeeStats(summary),
    projects: (summary.projects || []).map((project) => ({
      id: project.id,
      name: project.name,
      completionRate: project.completionRate,
      daysToDeadline: project.daysToDeadline
    })),
    pendingReviews: summary.pendingReviews || [],
    pendingReviewCount: summary.pendingReviewCount ?? 0,
    subUnits: (summary.subUnits || []).map((unit) => ({
      name: unit.name,
      points: unit.points
    })),
    subUnitLevelName: summary.subUnitLevelName || '单位',
    rankings: (summary.rankings || []).map((row) => ({
      rank: row.rank,
      name: row.name,
      organization: row.organization,
      points: row.points
    })),
    todayReported: Boolean(summary.todayReported),
    myScore: summary.myScore,
    myRank: summary.myRank,
    myRankScope: summary.myRankScope
  }
}

// 离线兜底：后端不可用时用本地 mock 拼一个最小可用看板，避免首页白屏。
function buildMockFallback(user) {
  const isManager = Boolean(user?.role && user.role !== 'employee')
  const inProgress = mockProjects.filter((project) => project.status === '进行中')

  const fallback = {
    viewType: isManager ? 'MANAGER' : 'EMPLOYEE',
    name: user?.name || '',
    organizationName: user?.organizationName || '',
    visibleProjectCount: mockProjects.length,
    activeProjectCount: inProgress.length,
    pendingReviewCount: 0,
    monthReportCount: 0,
    scopePoints: 0,
    overallCompletionRate: null,
    projects: inProgress.slice(0, 6).map((project) => ({
      id: project.id,
      name: project.name,
      completionRate: null,
      daysToDeadline: null
    })),
    pendingReviews: [],
    subUnits: [],
    subUnitLevelName: '单位',
    rankings: (mockRankingRows || []).slice(0, 5).map((row) => ({
      rank: row.rank,
      name: row.name,
      organization: row.organization,
      points: row.points
    })),
    todayReported: false,
    myScore: 0,
    myRank: null,
    myRankScope: '本月'
  }

  return normalizeSummary(fallback)
}

export async function getDashboardSummary(user) {
  try {
    const summary = await request('/api/admin/dashboard/summary')
    return normalizeSummary(summary)
  } catch (error) {
    return buildMockFallback(user)
  }
}
