<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h1>每日上报</h1>
        <p>员工选择项目与指标，填写完成数量，必要时上传附件。</p>
      </div>
      <span class="badge">上报表单</span>
    </header>

    <section class="grid grid-2">
      <form class="panel form-grid" @submit.prevent="submitReport">
        <label class="form-field">
          项目
          <select v-model="form.projectId" class="select">
            <option value="">请选择项目</option>
            <option v-for="project in projects" :key="project.id" :value="project.id">
              {{ project.name }} · {{ project.assignedFrom }}下发
            </option>
          </select>
        </label>

        <label class="form-field">
          指标
          <select v-model="form.indicatorId" class="select">
            <option value="">请选择指标</option>
            <option v-for="indicator in availableIndicators" :key="indicator.id" :value="indicator.id">
              {{ indicator.name }}
            </option>
          </select>
        </label>

        <label class="form-field">
          上报数量
          <input v-model.number="form.amount" class="field" type="number" min="0" />
        </label>

        <label class="form-field">
          附件
          <input class="field" type="file" @change="form.hasAttachment = true" />
        </label>

        <div class="form-field full">
          <button class="button primary" type="submit" :disabled="selectedProject?.status === '已结束'">
            提交上报
          </button>
          <p v-if="message" class="form-message">{{ message }}</p>
        </div>
      </form>

      <div class="panel">
        <h2>当前项目规则</h2>
        <p class="muted" v-if="!selectedProject">请选择项目后查看规则。</p>
        <dl v-else class="rules">
          <div>
            <dt>任务来源</dt>
            <dd>{{ selectedProject.assignedFrom }}下发</dd>
          </div>
          <div>
            <dt>项目状态</dt>
            <dd>{{ selectedProject.status }}</dd>
          </div>
          <div>
            <dt>每日截止</dt>
            <dd>{{ selectedProject.reportDeadline }}</dd>
          </div>
          <div>
            <dt>附件要求</dt>
            <dd>{{ selectedProject.attachmentRequired ? '必须上传附件' : '不强制附件' }}</dd>
          </div>
        </dl>
      </div>
    </section>

    <section class="panel">
      <h2>历史上报记录</h2>
      <table class="table">
        <thead>
          <tr>
            <th>项目</th>
            <th>指标</th>
            <th>上报人</th>
            <th>数量</th>
            <th>积分</th>
            <th>时间</th>
            <th>附件</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="report in reports" :key="report.id">
            <td>{{ report.project }}</td>
            <td>{{ report.indicator }}</td>
            <td>{{ report.reporter }}</td>
            <td>{{ report.amount }} {{ report.unit }}</td>
            <td>{{ report.points }}</td>
            <td>{{ report.reportedAt }}</td>
            <td>{{ report.attachment }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { getCurrentUser } from '../auth/permissions'
import { getMyReports, getReportOptions, submitReport as submitReportApi } from '../api/reports'

const indicators = ref([])
const projects = ref([])
const reports = ref([])
const currentUser = getCurrentUser()
const form = reactive({
  projectId: '',
  indicatorId: '',
  amount: null,
  hasAttachment: false
})
const message = ref('')

const selectedProject = computed(() => projects.value.find((project) => project.id === form.projectId))
const availableIndicators = computed(() =>
  indicators.value.filter((indicator) => indicator.projectId === form.projectId)
)

async function submitReport() {
  if (!form.projectId) {
    message.value = '项目不能为空。'
    return
  }
  if (!form.indicatorId) {
    message.value = '指标不能为空。'
    return
  }
  if (!form.amount || form.amount <= 0) {
    message.value = '上报数量必须大于 0。'
    return
  }
  if (selectedProject.value?.attachmentRequired && !form.hasAttachment) {
    message.value = '该项目要求上传附件。'
    return
  }

  await submitReportApi({ ...form })
  message.value = '上报内容已通过前端校验，等待接入后端提交接口。'
}

onMounted(async () => {
  const options = await getReportOptions(currentUser)
  projects.value = options.projects
  indicators.value = options.indicators
  reports.value = await getMyReports(currentUser)
})
</script>

<style scoped>
.form-message {
  margin: 0;
  color: #0f766e;
}

.rules {
  display: grid;
  gap: 12px;
}

.rules div {
  display: flex;
  justify-content: space-between;
  padding-bottom: 12px;
  border-bottom: 1px solid #e5e7eb;
}

dt {
  color: #6b7280;
}

dd {
  margin: 0;
  color: #111827;
  font-weight: 600;
}
</style>
