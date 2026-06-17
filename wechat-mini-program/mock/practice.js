// 陪练 mock
function growth() {
  return { level: 5, levelName: '专业进阶', points: 1260, target: 1800, weekGain: 320, streak: 7 }
}

function tasks() {
  return {
    assigned: [
      { id: 't1', name: '风险揭示话术', scene: '理财产品风险揭示', level: 'must', status: '进行中', deadline: '06/28', points: 50 },
      { id: 't2', name: '高净值客户需求挖掘', scene: '需求挖掘', level: 'recommend', status: '待完成', deadline: '07/05', points: 60 }
    ],
    library: [
      { id: 'l1', name: '信用卡分期回访', type: '实战', points: 40 },
      { id: 'l2', name: '贷款逾期提醒', type: '实战', points: 40 },
      { id: 'l3', name: '客户投诉安抚', type: '实战', points: 40 },
      { id: 'l4', name: '基金波动解释', type: '实战', points: 40 }
    ],
    done: [
      { id: 't0', name: '存款推荐话术', scene: '存款推荐', status: '已完成', score: 82, date: '06/10' }
    ]
  }
}

function taskDetail() {
  return {
    scene: '存款推荐',
    customerName: '王女士',
    customerDesc: '35岁，企业白领，有一笔闲置资金',
    tags: ['流动性担忧', '利率敏感', '风险厌恶'],
    rounds: 3,
    background: '客户近期有一笔闲置资金，关注收益的同时担心资金随时可能需要支取。请你结合客户情况，推荐合适的存款产品并打消其顾虑。',
    goal: '完成 3 轮对话，覆盖产品收益、流动性方案与风险说明。',
    requirements: ['完成 3 轮对话', '综合得分 ≥ 80 分', '提交复盘与优化话术'],
    duration: '15-20 分钟',
    progress: 0
  }
}

function dialogStart() {
  return {
    messages: [
      { role: 'ai', content: '您好，我最近想了解一下存款产品，有没有收益比较高又安全的推荐？' }
    ],
    round: 1
  }
}

function dialogReply(round) {
  return {
    message: { role: 'ai', content: `（第${round}轮）那如果资金需要随时支取，您会怎么建议？` },
    round
  }
}

function result(score) {
  return {
    score: score != null ? score : 82,
    delta: 6,
    cert: '新晋「合规揭示达人」',
    certDesc: '合规表达达标，完成专项认证',
    dimensions: [
      { label: '合规度', value: 92, level: '优秀' },
      { label: '共情力', value: 84, level: '良好' },
      { label: '逻辑结构', value: 86, level: '优秀' },
      { label: '异议处理', value: 80, level: '良好' }
    ],
    rewardPoints: 80,
    rewardExp: 120,
    suggestion: '回答基本覆盖了产品要点，但对客户流动性需求的应对不够具体，建议补充活期与定期搭配方案的说明。'
  }
}

function review() {
  return {
    original: '这款产品风险不大，主要投债券，历史上波动也比较小，您可以放心一些。',
    optimized: '您关注本金安全是非常合理的。这款产品主要投资于高评级债券与货币工具，整体波动较低，过去三年最大回撤控制在较小范围；同时支持灵活赎回，兼顾收益与流动性，能较好匹配您的需求。'
  }
}

function history() {
  return [
    { id: 1, scene: '存款推荐', score: 82, date: '2026-06-14' },
    { id: 2, scene: '存款推荐', score: 75, date: '2026-06-10' }
  ]
}

module.exports = { growth, tasks, taskDetail, dialogStart, dialogReply, result, review, history }
