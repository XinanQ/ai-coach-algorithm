// 管理端 mock
function workspaceStats() {
  return {
    completionRate: 86, completionDelta: 9,
    avgScore: 82, avgDelta: 5,
    pendingCount: 24, highRiskCount: 7
  }
}

function workspaceRanking() {
  return [
    { rank: 1, name: '李晨', dept: '客户经理', rate: 95, score: 88 },
    { rank: 2, name: '王敏', dept: '理财顾问', rate: 78, score: 81 },
    { rank: 3, name: '张瑞', dept: '客户经理', rate: 72, score: 79 },
    { rank: 4, name: '张洁', dept: '客户经理', rate: 68, score: 75 },
    { rank: 5, name: '刘洋', dept: '理财顾问', rate: 60, score: 72 }
  ]
}

function assign() {
  return { id: 'task-' + Date.now() }
}

function taskTemplates() {
  return [
    { id: 'tt1', name: '理财产品风险揭示话术', scene: '风险揭示', dimensions: 4 },
    { id: 'tt2', name: '信用卡分期回访', scene: '信用卡', dimensions: 3 },
    { id: 'tt3', name: '贷款逾期提醒', scene: '贷款', dimensions: 3 },
    { id: 'tt4', name: '客户投诉安抚', scene: '投诉', dimensions: 4 }
  ]
}

function analysis() {
  return {
    team: { completionRate: 86, avgScore: 82, recommendRate: 76, highRiskCount: 7 },
    completionTop3: [
      { name: '李晨', value: 95 },
      { name: '陈晓', value: 90 },
      { name: '王敏', value: 78 }
    ],
    abilityTop3: [
      { name: '风险揭示话术', count: 32 },
      { name: '客户异议处理', count: 26 },
      { name: '合规表达达成', count: 21 }
    ]
  }
}

function employees() {
  return [
    { id: 'e1', name: '李晨', dept: '客户经理', rate: 95, score: 88, progress: 90 },
    { id: 'e2', name: '王敏', dept: '理财顾问', rate: 78, score: 81, progress: 70 },
    { id: 'e3', name: '张瑞', dept: '客户经理', rate: 72, score: 79, progress: 65 },
    { id: 'e4', name: '张洁', dept: '客户经理', rate: 68, score: 75, progress: 60 },
    { id: 'e5', name: '刘洋', dept: '理财顾问', rate: 60, score: 72, progress: 55 }
  ]
}

function employeeDetail(id) {
  return {
    id,
    name: '李晨',
    dept: '客户经理',
    rate: 95,
    score: 88,
    tasks: [
      { name: '风险揭示话术', status: '已完成', score: 88 },
      { name: '高净值客户需求挖掘', status: '进行中', score: null },
      { name: '客户投诉安抚', status: '已完成', score: 84 }
    ]
  }
}

module.exports = {
  workspaceStats, workspaceRanking, assign, taskTemplates, analysis, employees, employeeDetail
}
