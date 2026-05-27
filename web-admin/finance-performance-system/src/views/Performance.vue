<template>
  <div class="page">
    <h1>绩效数据管理</h1>

    <table>
      <thead>
        <tr>
          <th>员工姓名</th>
          <th>部门</th>
          <th>绩效分数</th>
          <th>奖金</th>
        </tr>
      </thead>

      <tbody>
        <tr v-for="item in tableData" :key="item.name">
          <td>{{ item.name }}</td>
          <td>{{ item.department }}</td>
          <td>{{ item.score }}</td>
          <td>{{ item.bonus }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
const tableData = [
  {
    name: '张三',
    department: '金融业务部',
    score: 92,
    bonus: 12000
  },
  {
    name: '李四',
    department: '风控部',
    score: 86,
    bonus: 9000
  },
  {
    name: '王五',
    department: '客户管理部',
    score: 78,
    bonus: 7000
  }
]
</script>

<style scoped>
.page {
  padding: 24px;
}

table {
  width: 100%;
  border-collapse: collapse;
  background: white;
}

th,
td {
  border: 1px solid #ddd;
  padding: 12px;
  text-align: left;
}

th {
  background: #f5f7fa;
}
</style>