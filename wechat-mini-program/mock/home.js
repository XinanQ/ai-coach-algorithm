// 首页 mock（GET /api/mini/home）
// 字段对齐后端规范；demo 用非零数据让页面看起来已填充
function home() {
  return {
    name: '张三',
    level: 'STAFF',
    isAdmin: false,
    organizationId: 4,
    organizationName: 'XX网点',
    monthlyScore: 86,
    scoreTarget: 120,
    completionRate: 72,
    rank: 12,
    rankScope: '网点排名',
    todayReported: false,
    pendingPracticeTaskCount: 1
  }
}

module.exports = { home }
