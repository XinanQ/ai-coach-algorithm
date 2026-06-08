<template>
  <div class="page forbidden-page">
    <section class="panel forbidden-panel">
      <span class="badge">403</span>
      <h1>当前角色无权访问该页面</h1>
      <p>
        {{ currentUser?.roleName || '当前用户' }} 的数据范围是
        {{ currentUser?.dataScope || '未获取' }}，请切换有权限的角色后再访问。
      </p>
      <div class="toolbar">
        <router-link class="button primary" :to="defaultPath">返回可访问首页</router-link>
        <button class="button" type="button" @click="switchRole">切换角色</button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { clearCurrentUser, getCurrentUser, getDefaultPath } from '../auth/permissions'

const router = useRouter()
const currentUser = getCurrentUser()
const defaultPath = computed(() => getDefaultPath(currentUser))

function switchRole() {
  clearCurrentUser()
  router.push('/login')
}
</script>

<style scoped>
.forbidden-page {
  min-height: calc(100svh - 48px);
  align-content: center;
}

.forbidden-panel {
  max-width: 620px;
}

.forbidden-panel h1 {
  margin: 12px 0 8px;
}

.forbidden-panel p {
  margin-bottom: 20px;
  color: #6b7280;
}
</style>
