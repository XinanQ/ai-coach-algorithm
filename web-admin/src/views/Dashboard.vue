<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h1>首页数据概览</h1>
        <p>
          {{ currentUser.position || currentUser.roleName || '未设置职位' }}
          ·
          {{ currentUser.organizationName || currentUser.organization || '未设置机构' }}，数据范围：{{ currentUser.dataScope }}。
        </p>
      </div>
      <router-link v-if="canManageProjects" class="button primary" to="/projects">进入项目管理</router-link>
      <router-link v-else class="button primary" to="/report">进入每日上报</router-link>
    </header>

    <template v-if="currentUser.role === 'city_admin'">
      <section class="grid grid-4 city-dashboard">
        <el-card v-for="item in dashboardStats" :key="item.label" shadow="hover" class="stat-card-modern">
          <div class="stat-content">
            <div class="stat-label">{{ item.label }}</div>
            <div class="stat-value">{{ item.value }}</div>
            <div class="stat-hint">{{ item.hint }}</div>
          </div>
        </el-card>
      </section>

      <section class="grid grid-2 city-charts">
        <el-card shadow="hover">
          <template #header>
            <span style="font-weight: 600; font-size: 16px;">📈 项目完成趋势</span>
          </template>
          <div ref="trendChartEl" style="width: 100%; height: 280px;"></div>
        </el-card>

        <el-card shadow="hover">
          <template #header>
            <span style="font-weight: 600; font-size: 16px;">🏆 积分排名 Top 5</span>
          </template>
          <div ref="rankingChartEl" style="width: 100%; height: 280px;"></div>
        </el-card>
      </section>

      <section class="grid grid-2 city-tables">
        <el-card shadow="hover">
          <template #header>
            <span style="font-weight: 600; font-size: 16px;">📋 项目进度</span>
          </template>
          <el-table :data="projects" stripe size="small" empty-text="暂无项目数据">
            <el-table-column prop="name" label="项目名称" />
            <el-table-column prop="status" label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.status === '进行中' ? 'success' : 'info'" size="small">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="完成率" width="180" align="center">
              <template #default="{ row }">
                <ProgressBar :value="row.status === '进行中' ? 86 : 0" />
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card shadow="hover">
          <template #header>
            <span style="font-weight: 600; font-size: 16px;">⭐ 积分排行榜</span>
          </template>
          <el-table :data="rankingRows.slice(0, 5)" stripe size="small" empty-text="暂无排名数据">
            <el-table-column prop="rank" label="排名" width="70" align="center" />
            <el-table-column prop="name" label="人员" />
            <el-table-column prop="organization" label="机构" />
            <el-table-column prop="points" label="积分" width="80" align="right">
              <template #default="{ row }">
                <span style="font-weight: 600; color: #0f766e;">{{ row.points }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </section>
    </template>

    <template v-else>
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
    </template>
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
const trendChartEl = ref(null)
const rankingChartEl = ref(null)
let chartInstance = null
let trendChartInstance = null
let rankingChartInstance = null
const canManageProjects = computed(() =>
  ['head_admin', 'province_admin', 'city_admin', 'branch_admin'].includes(currentUser?.role)
)

function renderTrendChart() {
  if (!trendChartEl.value) return

  trendChartInstance?.dispose()
  trendChartInstance = echarts.init(trendChartEl.value)
  const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
  const completionData = [45, 52, 61, 70, 78, 86, 92]
  const targetData = [50, 60, 70, 80, 90, 100, 100]

  trendChartInstance.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    legend: {
      data: ['实际完成率', '目标完成率'],
      bottom: -8,
      textStyle: {
        fontSize: 12
      }
    },
    grid: { left: 48, right: 16, top: 16, bottom: 44 },
    xAxis: {
      type: 'category',
      data: days,
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#ddd' } },
      axisLabel: { color: '#666' }
    },
    yAxis: {
      type: 'value',
      max: 100,
      axisLabel: { formatter: '{value}%', color: '#666' },
      splitLine: { lineStyle: { color: '#f0f0f0' } }
    },
    series: [
      {
        name: '实际完成率',
        type: 'line',
        data: completionData,
        smooth: true,
        lineStyle: { color: '#0f766e', width: 3 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(15, 118, 110, 0.3)' },
            { offset: 1, color: 'rgba(15, 118, 110, 0.05)' }
          ])
        },
        itemStyle: { color: '#0f766e' }
      },
      {
        name: '目标完成率',
        type: 'line',
        data: targetData,
        smooth: true,
        lineStyle: { color: '#e5e7eb', width: 2, type: 'dashed' },
        itemStyle: { color: '#9ca3af' }
      }
    ]
  })
}

function renderRankingChart() {
  if (!rankingChartEl.value) return

  rankingChartInstance?.dispose()
  rankingChartInstance = echarts.init(rankingChartEl.value)
  const top5Data = rankingRows.value.slice(0, 5).reverse()

  rankingChartInstance.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 72, right: 24, top: 16, bottom: 24 },
    xAxis: {
      type: 'value',
      axisLabel: { color: '#666' },
      splitLine: { lineStyle: { color: '#f0f0f0' } }
    },
    yAxis: {
      type: 'category',
      data: top5Data.map(row => row.name),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#333', fontSize: 13 }
    },
    series: [
      {
        type: 'bar',
        data: top5Data.map((row, index) => ({
          value: row.points,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: index === top5Data.length - 1 ? '#fbbf24' : '#0f766e' },
              { offset: 1, color: index === top5Data.length - 1 ? '#f59e0b' : '#14b8a6' }
            ]),
            borderRadius: [0, 4, 4, 0]
          }
        })),
        barMaxWidth: 28,
        label: {
          show: true,
          position: 'right',
          color: '#333',
          fontWeight: 600
        }
      }
    ]
  })
}

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

  if (currentUser.role === 'city_admin') {
    renderTrendChart()
    renderRankingChart()
  } else {
    renderChart()
  }
})

onBeforeUnmount(() => {
  chartInstance?.dispose()
  trendChartInstance?.dispose()
  rankingChartInstance?.dispose()
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

.city-dashboard {
  margin-bottom: 20px;
}

.stat-card-modern {
  text-align: center;
  padding: 20px 16px;
}

.stat-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.stat-label {
  font-size: 14px;
  color: #666;
  font-weight: 500;
}

.stat-value {
  font-size: 36px;
  color: #0f766e;
  font-weight: 700;
  line-height: 1.2;
}

.stat-hint {
  font-size: 13px;
  color: #999;
}

.city-charts,
.city-tables {
  gap: 20px;
  margin-bottom: 20px;
}

.city-charts :deep(.el-card__header),
.city-tables :deep(.el-card__header) {
  padding: 12px 20px;
  border-bottom: 1px solid #ebeef5;
}
</style>
