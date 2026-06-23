// 话术库 mock（字段对齐 GET /api/mini/scripts[/{scriptId}]）
function list() {
  return [
    { scriptId: 's1', scene: '理财产品风险揭示', title: '稳健型客户风险揭示', tags: ['合规表达', '风险提示'], date: '06/12' },
    { scriptId: 's2', scene: '存款推荐', title: '流动性需求应对', tags: ['异议处理'], date: '06/10' }
  ]
}

function detail(id) {
  return {
    scriptId: id || 's1',
    scene: '理财产品风险揭示',
    title: '稳健型客户风险揭示',
    tags: ['合规表达', '风险提示'],
    standard: '您关注本金安全是非常合理的。这款产品主要投资于高评级债券与货币工具，整体波动较低，过去三年最大回撤控制在较小范围；同时它支持灵活赎回，兼顾收益与流动性。',
    sourceTaskId: 't1',
    // mine 为前端演示字段（规范未定义），后端不返回时下方「我的优化话术」区块自动隐藏
    mine: '这款产品风险不大，主要投债券，历史上波动也比较小，您可以放心一些。'
  }
}

function save() {
  return { scriptId: 'script-' + Date.now() }
}

module.exports = { list, detail, save }
