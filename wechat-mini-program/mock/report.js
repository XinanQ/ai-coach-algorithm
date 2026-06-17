// 业绩上报 mock
function indicators() {
  return [
    { id: 1, name: '存款净增额', unit: '万元' },
    { id: 2, name: '理财销售额', unit: '万元' },
    { id: 3, name: '信用卡发卡量', unit: '张' }
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

module.exports = { indicators, history, submit }
