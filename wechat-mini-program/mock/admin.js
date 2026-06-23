// 管理端 mock（字段对齐《微信小程序接口联调说明》管理员接口）

// GET /api/mini/admin/workspace —— 统计 + 员工排行合并返回
function workspace() {
  return {
    completionRate: 86,
    completionDelta: 9,
    avgScore: 82,
    avgDelta: 5,
    pendingCount: 24,
    highRiskCount: 7,
    ranking: [
      { rank: 1, employeeId: 1, name: '李晨', position: '客户经理', completionRate: 95, score: 88 },
      { rank: 2, employeeId: 2, name: '王敏', position: '理财顾问', completionRate: 78, score: 81 },
      { rank: 3, employeeId: 3, name: '张瑞', position: '客户经理', completionRate: 72, score: 79 },
      { rank: 4, employeeId: 4, name: '张洁', position: '客户经理', completionRate: 68, score: 75 },
      { rank: 5, employeeId: 5, name: '刘洋', position: '理财顾问', completionRate: 60, score: 72 }
    ]
  }
}

function assign() {
  return { taskId: 'task-' + Date.now() }
}

// GET /api/mini/admin/practice/templates
function taskTemplates() {
  return [
    { templateId: 'tpl1', name: '理财产品风险揭示话术', scene: '风险揭示', dimensionCount: 4 },
    { templateId: 'tpl2', name: '信用卡分期回访', scene: '信用卡', dimensionCount: 3 },
    { templateId: 'tpl3', name: '贷款逾期提醒', scene: '贷款', dimensionCount: 3 },
    { templateId: 'tpl4', name: '客户投诉安抚', scene: '投诉', dimensionCount: 4 }
  ]
}

// GET /api/mini/admin/practice/templates/{templateId}
function templateDetail(id) {
  return {
    templateId: id || 'tpl1',
    name: '理财产品风险揭示话术',
    scene: '风险揭示',
    dimensions: ['合规表达', '风险提示', '客户异议处理', '成交推进']
  }
}

// GET /api/mini/admin/analysis?period=week|month
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

// GET /api/mini/admin/employees
function employees() {
  return [
    { employeeId: 1, name: '李晨', position: '客户经理', completionRate: 95, score: 88, progress: 90 },
    { employeeId: 2, name: '王敏', position: '理财顾问', completionRate: 78, score: 81, progress: 70 },
    { employeeId: 3, name: '张瑞', position: '客户经理', completionRate: 72, score: 79, progress: 65 },
    { employeeId: 4, name: '张洁', position: '客户经理', completionRate: 68, score: 75, progress: 60 },
    { employeeId: 5, name: '刘洋', position: '理财顾问', completionRate: 60, score: 72, progress: 55 }
  ]
}

// 员工详情：规范未定义，前端演示用（保留原形状）
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
  workspace, assign, taskTemplates, templateDetail, analysis, employees, employeeDetail
}
