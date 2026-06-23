<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h1>人员管理</h1>
        <p>维护员工基础信息、所属机构、员工类型与管理员身份。</p>
      </div>
      <button class="button primary" type="button" @click="goEmployeeManage">新增人员</button>
    </header>

    <section class="panel toolbar">
      <select v-model="filters.organization" class="select">
        <option value="">全部机构</option>
        <option v-for="organization in organizationOptions" :key="organization">
          {{ organization }}
        </option>
      </select>
      <select v-model="filters.isNew" class="select">
        <option value="">全部员工</option>
        <option value="true">新员工</option>
        <option value="false">非新员工</option>
      </select>
      <select v-model="filters.workType" class="select">
        <option value="">内勤/外勤</option>
        <option>内勤</option>
        <option>外勤</option>
      </select>
      <select v-model="filters.isAdmin" class="select">
        <option value="">全部权限</option>
        <option value="true">管理员</option>
        <option value="false">普通员工</option>
      </select>
    </section>

    <section class="panel">
      <table class="table">
        <thead>
          <tr>
            <th>姓名</th>
            <th>邮箱</th>
            <th>职务</th>
            <th>所属机构</th>
            <th>员工类型</th>
            <th>权限</th>
            <th>参与项目</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in filteredUsers" :key="user.id">
            <td>{{ user.name }}</td>
            <td>{{ user.email }}</td>
            <td>{{ user.position }}</td>
            <td>{{ user.organization }}</td>
            <td>{{ user.isNew ? '新员工' : '非新员工' }} · {{ user.workType }}</td>
            <td><span class="badge">{{ user.isAdmin ? '管理员' : '普通员工' }}</span></td>
            <td>{{ user.joinedProject ? '是' : '否' }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getUsers } from '../api/users'

const router = useRouter()
const users = ref([])

const filters = reactive({
  organization: '',
  isNew: '',
  workType: '',
  isAdmin: ''
})

const filteredUsers = computed(() =>
  users.value.filter((user) => {
    if (filters.organization && user.organization !== filters.organization) return false
    if (filters.workType && user.workType !== filters.workType) return false
    if (filters.isNew && String(user.isNew) !== filters.isNew) return false
    if (filters.isAdmin && String(user.isAdmin) !== filters.isAdmin) return false
    return true
  })
)

const organizationOptions = computed(() =>
  [...new Set(users.value.map((user) => user.organization))].sort((a, b) => a.localeCompare(b, 'zh-Hans-CN'))
)

function goEmployeeManage() {
  router.push('/users/employee-manage')
}

onMounted(async () => {
  users.value = await getUsers()
})
</script>