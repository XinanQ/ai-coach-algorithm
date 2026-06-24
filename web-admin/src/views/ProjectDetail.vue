<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h1>{{ project.name }}</h1>
        <p>{{ project.description }}</p>
      </div>
      <span class="badge">{{ project.status }}</span>
    </header>

    <section class="grid grid-4">
      <article class="stat-card">
        <span>项目周期</span>
        <strong>{{ project.startDate }}</strong>
        <small>至 {{ project.endDate }}</small>
      </article>
      <article class="stat-card">
        <span>上报截止</span>
        <strong>{{ project.reportDeadline }}</strong>
        <small>每日截止时间</small>
      </article>
      <article class="stat-card">
        <span>附件要求</span>
        <strong>{{ project.attachmentRequired ? '必传' : '选传' }}</strong>
        <small>影响每日上报校验</small>
      </article>
      <article class="stat-card">
        <span>指标数量</span>
        <strong>{{ projectIndicators.length }}</strong>
        <small>已配置业务指标</small>
      </article>
    </section>

    <section class="panel">
      <h2>项目指标</h2>
      <table class="table">
        <thead>
          <tr>
            <th>指标名称</th>
            <th>类型</th>
            <th>单位</th>
            <th>积分标准</th>
            <th>占比</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="indicator in projectIndicators" :key="indicator.id">
            <td>{{ indicator.name }}</td>
            <td>{{ indicator.indicatorType }}</td>
            <td>{{ indicator.unit }}</td>
            <td>{{ indicator.pointRule }} 分 / {{ indicator.unit }}</td>
            <td>{{ indicator.weight }}%</td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getProject, getProjectIndicators } from '../api/projects'

const route = useRoute()
const project = ref({})
const projectIndicators = ref([])

const indicatorTypeMap = { PROCESS: '过程指标', RESULT: '结果指标' }

async function loadProject() {
  project.value = await getProject(route.params.id)
  const raw = await getProjectIndicators(route.params.id)
  projectIndicators.value = (raw || []).map((ind) => ({
    id: ind.id,
    name: ind.indicatorName,
    indicatorType: indicatorTypeMap[ind.indicatorType] || ind.indicatorType || '',
    unit: ind.unit,
    pointRule: Number(ind.pointsStandard),
    weight: Math.round(Number(ind.ratio) * 100)
  }))
}

onMounted(loadProject)
watch(() => route.params.id, loadProject)
</script>
