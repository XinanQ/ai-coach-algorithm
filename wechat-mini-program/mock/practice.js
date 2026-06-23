// 陪练 mock（字段对齐《微信小程序接口联调说明》）

// GET /api/mini/practice/tasks?tab=assigned|self|done
// 成长信息随任务列表一起返回；list 仅含当前 tab 的任务
function tasks(tab) {
  const growth = { levelName: 'Lv5 专业进阶', points: 1260, target: 1800, streakDays: 7, weekGain: 320 }
  const lists = {
    assigned: [
      { taskId: 't1', title: '风险揭示话术', scene: '理财产品风险揭示', level: 'must', status: 'IN_PROGRESS', deadline: '2026-06-28', rewardPoints: 50 },
      { taskId: 't2', title: '高净值客户需求挖掘', scene: '需求挖掘', level: 'recommend', status: 'PENDING', deadline: '2026-07-05', rewardPoints: 60 }
    ],
    self: [
      { taskId: 'l1', title: '信用卡分期回访', scene: '信用卡', level: 'recommend', status: 'PENDING', deadline: '', rewardPoints: 40 },
      { taskId: 'l2', title: '贷款逾期提醒', scene: '贷款', level: 'recommend', status: 'PENDING', deadline: '', rewardPoints: 40 },
      { taskId: 'l3', title: '客户投诉安抚', scene: '投诉', level: 'recommend', status: 'PENDING', deadline: '', rewardPoints: 40 },
      { taskId: 'l4', title: '基金波动解释', scene: '基金', level: 'recommend', status: 'PENDING', deadline: '', rewardPoints: 40 }
    ],
    done: [
      { taskId: 't0', title: '存款推荐话术', scene: '存款推荐', level: 'must', status: 'DONE', deadline: '2026-06-10', rewardPoints: 50 }
    ]
  }
  return Object.assign({}, growth, { list: lists[tab] || lists.assigned })
}

// GET /api/mini/practice/tasks/{taskId}
function taskDetail(taskId) {
  return {
    taskId: taskId || 't1',
    scene: '存款推荐',
    rounds: 3,
    customerName: '王女士',
    customerDesc: '35岁，企业白领，有一笔闲置资金',
    tags: ['流动性担忧', '利率敏感', '风险厌恶'],
    background: '客户近期有一笔闲置资金，关注收益的同时担心资金随时可能需要支取。请你结合客户情况，推荐合适的存款产品并打消其顾虑。',
    goal: '完成 3 轮对话，覆盖产品收益、流动性方案与风险说明。',
    requirements: ['完成 3 轮对话', '综合得分 ≥ 80 分', '提交复盘与优化话术'],
    duration: '15-20 分钟',
    progress: 0
  }
}

// POST /api/mini/practice/dialog/start
function dialogStart() {
  return {
    sessionId: 's' + Date.now(),
    round: 1,
    totalRounds: 3,
    liveScore: 70,
    messages: [
      { role: 'ai', content: '您好，我最近想了解一下存款产品，有没有收益比较高又安全的推荐？' }
    ]
  }
}

// POST /api/mini/practice/dialog/reply
// round 为用户刚作答的轮次，mock 据此推进到下一轮；超过总轮次则 finished=true
function dialogReply(round) {
  const totalRounds = 3
  const cur = round || 1
  const nextRound = cur + 1
  const finished = nextRound > totalRounds
  return {
    round: finished ? totalRounds : nextRound,
    totalRounds,
    liveScore: Math.min(95, 66 + nextRound * 6),
    message: finished
      ? null
      : { role: 'ai', content: `（第${nextRound}轮）如果资金需要随时支取，您会怎么建议呢？` },
    finished
  }
}

// POST /api/mini/practice/dialog/finish
function dialogFinish() {
  return {
    resultId: 'r' + Date.now(),
    taskId: 't1',
    score: 82,
    weakTags: ['流动性解释不足', '风险提示不足'],
    suggestion: '建议补充提前支取规则，并避免绝对化收益表达。'
  }
}

// —— 以下为前端演示页 mock（规范未定义）——
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

module.exports = {
  tasks, taskDetail,
  dialogStart, dialogReply, dialogFinish,
  result, review, history
}
