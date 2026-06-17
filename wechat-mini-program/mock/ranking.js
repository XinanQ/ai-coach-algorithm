// 排行榜 mock
function ranking() {
  const list = []
  for (let i = 1; i <= 10; i++) {
    list.push({ rank: i, name: `员工${i}`, score: 100 - i * 3 })
  }
  return { myRank: 12, myScore: 86, list }
}

module.exports = { ranking }
