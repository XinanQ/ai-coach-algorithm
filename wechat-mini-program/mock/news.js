// 喜报 mock
const list = [
  {
    id: 1,
    title: '存款大单喜报',
    date: '2026-06-14',
    recipient: '张三',
    content: '恭喜张三在 2026-06-14 达成存款大单，单笔存款净增额 50 万元，业绩突出，特此表彰！',
    imageUrl: ''
  },
  {
    id: 2,
    title: '单日积分排名第一',
    date: '2026-06-10',
    recipient: '张三',
    content: '恭喜张三在 2026-06-10 以 96 分摘得本网点单日积分排名第一，再接再厉！',
    imageUrl: ''
  }
]

function getList() {
  return list.map(({ id, title, date }) => ({ id, title, date }))
}

function getDetail(id) {
  return list.find(item => String(item.id) === String(id)) || null
}

module.exports = { getList, getDetail }
