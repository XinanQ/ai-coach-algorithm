// 业绩上报 mock
function projects() {
  return [
    { id: 1, name: '2026 春季旺季营销项目', status: '进行中', statusCode: 'ACTIVE' },
    { id: 3, name: '2026 企业微信客户拓展项目', status: '进行中', statusCode: 'ACTIVE' }
  ]
}

function indicators() {
  return [
    { id: 1, projectId: 1, name: '存款净增额', unit: '万元' },
    { id: 2, projectId: 1, name: '定期存款', unit: '万元' },
    { id: 3, projectId: 3, name: '企业微信添加量', unit: '户' }
  ]
}

function history() {
  return [
    { id: 1, date: '2026-06-14', indicator: '存款净增额', value: '8.5万元', status: '已通过', statusClass: 'approved' },
    { id: 2, date: '2026-06-13', indicator: '理财销售额', value: '3万元', status: '驳回', statusClass: 'rejected', reason: '附件不清晰' },
    { id: 3, date: '2026-06-12', indicator: '存款净增额', value: '5万元', status: '待审核', statusClass: 'pending' }
  ]
}

function submit() {
  return { id: Date.now() }
}

module.exports = { projects, indicators, history, submit }
