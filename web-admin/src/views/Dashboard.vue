<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h1>首页数据概览</h1>
        <p>{{ currentUser.roleName }} · {{ currentUser.organization }}，数据范围：{{ currentUser.dataScope }}。</p>
      </div>
      <router-link v-if="canManageProjects" class="button primary" to="/projects">进入项目管理</router-link>
      <router-link v-else class="button primary" to="/report">进入每日上报</router-link>
    </header>

    <section class="grid grid-4">
      <article v-for="item in dashboardStats" :key="item.label" class="stat-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <small>{{ item.hint }}</small>
      </article>
    </section>

    <el-alert
      class="library-check"
      title="Element Plus 已接入"
      type="success"
      description="该提示条使用 Element Plus 渲染，用于验证组件库状态。"
      show-icon
      :closable="false"
    />

    <section class="grid grid-2">
      <div class="panel">
        <h2>项目进度</h2>
        <table class="table">
          <thead>
            <tr>
              <th>项目</th>
              <th>状态</th>
              <th>完成率</th>
            </tr>
          </thead>
          <tbody v-if="projects.length">
            <tr v-for="project in projects" :key="project.id">
              <td>{{ project.name }}</td>
              <td><span class="badge">{{ project.status }}</span></td>
              <td>
                <ProgressBar :value="project.status === '进行中' ? 86 : 0" />
              </td>
            </tr>
          </tbody>
          <tbody v-else>
            <tr>
              <td colspan="3" class="muted">当前权限范围暂无可见项目。</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="panel">
        <h2>积分 Top 3</h2>
        <table class="table">
          <thead>
            <tr>
              <th>排名</th>
              <th>人员</th>
              <th>机构</th>
              <th>积分</th>
            </tr>
          </thead>
          <tbody v-if="rankingRows.length">
            <tr v-for="row in rankingRows" :key="row.rank">
              <td>{{ row.rank }}</td>
              <td>{{ row.name }}</td>
              <td>{{ row.organization }}</td>
              <td>{{ row.points }}</td>
            </tr>
          </tbody>
          <tbody v-else>
            <tr>
              <td colspan="4" class="muted">当前权限范围暂无排名数据。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel">
      <h2>积分图表</h2>
      <div ref="chartEl" class="mini-chart"></div>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import ProgressBar from '../components/ProgressBar.vue'
import { getCurrentUser } from '../auth/permissions'
import { getDashboardSummary } from '../api/dashboard'

const currentUser = getCurrentUser()
const dashboardStats = ref([])
const projects = ref([])
const rankingRows = ref([])
const chartEl = ref(null)
let chartInstance = null
const canManageProjects = computed(() =>
  ['head_admin', 'province_admin', 'city_admin', 'branch_admin'].includes(currentUser?.role)
)

function renderChart() {
  if (!chartEl.value) return

  chartInstance?.dispose()
  chartInstance = echarts.init(chartEl.value)
  chartInstance.setOption({
    grid: { left: 36, right: 16, top: 24, bottom: 28 },
    tooltip: {},
    xAxis: {
      type: 'category',
      data: rankingRows.value.map((row) => row.name)
    },
    yAxis: { type: 'value' },
    series: [
      {
        type: 'bar',
        data: rankingRows.value.map((row) => row.points),
        itemStyle: { color: '#0f766e' },
        barMaxWidth: 36
      }
    ]
  })
}

onMounted(async () => {
  const summary = await getDashboardSummary(currentUser)
  dashboardStats.value = summary.stats
  projects.value = summary.projects
  rankingRows.value = summary.rankings
  await nextTick()
  renderChart()
})

onBeforeUnmount(() => {
  chartInstance?.dispose()
})
</script>

<style scoped>
.library-check {
  border-radius: 8px;
}

.mini-chart {
  width: 100%;
  height: 240px;
}
</style>
