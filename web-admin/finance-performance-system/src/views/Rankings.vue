<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h1>积分排名</h1>
        <p>按项目、组织层级、指标和员工类型查看绩效积分排名。</p>
      </div>
      <router-link class="button" to="/dashboard">返回概览</router-link>
    </header>

    <section class="panel toolbar">
      <select v-model="filters.project" class="select">
        <option value="">全部项目</option>
        <option v-for="project in projects" :key="project.id">{{ project.name }}</option>
      </select>
      <select v-model="filters.level" class="select">
        <option value="">全部层级</option>
        <option>网点</option>
        <option>支行</option>
        <option>市行</option>
      </select>
      <select v-model="filters.indicator" class="select">
        <option value="">全部指标</option>
        <option v-for="indicator in indicators" :key="indicator.id">{{ indicator.name }}</option>
      </select>
      <select v-model="filters.employeeType" class="select">
        <option value="">全部员工</option>
        <option>新员工</option>
        <option>非新员工</option>
      </select>
    </section>

    <section class="panel">
      <table class="table">
        <thead>
          <tr>
            <th>排名</th>
            <th>人员</th>
            <th>机构</th>
            <th>主指标</th>
            <th>完成量</th>
            <th>积分</th>
            <th>完成率</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rankingRows" :key="row.rank">
            <td>{{ row.rank }}</td>
            <td>{{ row.name }}</td>
            <td>{{ row.organization }}</td>
            <td>{{ row.indicator }}</td>
            <td>{{ row.achievement }}</td>
            <td>{{ row.points }}</td>
            <td><ProgressBar :value="row.completionRate" /></td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import ProgressBar from '../components/ProgressBar.vue'
import { getCurrentUser } from '../auth/permissions'
import { getRankingOptions, getRankings } from '../api/rankings'

const indicators = ref([])
const projects = ref([])
const rankingRows = ref([])
const currentUser = getCurrentUser()

const filters = reactive({
  project: '',
  level: '',
  indicator: '',
  employeeType: ''
})

onMounted(async () => {
  const options = await getRankingOptions(currentUser)
  projects.value = options.projects
  indicators.value = options.indicators
  rankingRows.value = await getRankings(currentUser)
})
</script>
