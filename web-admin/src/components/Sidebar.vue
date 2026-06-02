<template>
  <aside class="side-banner">
    <div class="brand-area">
      <h2>金融业务绩效管理系统</h2>
      <p>Finance Performance</p>
    </div>

    <div v-if="currentUser" class="user-card">
      <strong>{{ currentUser.roleName }}</strong>
      <span>{{ currentUser.organization }}</span>
    </div>

    <nav class="side-nav">
      <router-link v-for="item in visibleMenus" :key="item.path" :to="item.path">
        {{ item.label }}
      </router-link>
    </nav>

    <button class="logout-button" type="button" @click="handleLogout">
      登出
    </button>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { clearCurrentUser, getCurrentUser, getVisibleMenus } from '../auth/permissions'

const router = useRouter()
const currentUser = computed(() => getCurrentUser())
const visibleMenus = computed(() => getVisibleMenus(currentUser.value))

function handleLogout() {
  clearCurrentUser()
  router.push('/login')
}
</script>

<style scoped>
.side-banner {
  width: 252px;
  height: 100svh;
  flex: 0 0 252px;
  overflow-y: auto;
  padding: 24px 18px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  background: #111827;
  color: white;
}

.brand-area {
  padding: 4px 6px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.14);
}

.brand-area h2 {
  margin: 0 0 8px;
  color: white;
  font-size: 18px;
  line-height: 1.35;
}

.brand-area p {
  color: #9ca3af;
  font-size: 13px;
}

.user-card {
  margin-top: 16px;
  padding: 12px;
  display: grid;
  gap: 4px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.08);
}

.user-card strong {
  color: #fff;
  font-size: 14px;
}

.user-card span {
  color: #cbd5e1;
  font-size: 13px;
}

.side-nav {
  display: grid;
  gap: 8px;
  padding: 20px 0;
}

.side-nav a {
  padding: 10px 12px;
  border-radius: 6px;
  color: #d1d5db;
  text-decoration: none;
  font-size: 15px;
}

.side-nav a:hover,
.side-nav a.router-link-active {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.logout-button {
  width: 100%;
  height: 40px;
  margin-top: auto;
  border: 1px solid rgba(255, 255, 255, 0.28);
  border-radius: 6px;
  background: transparent;
  color: white;
  cursor: pointer;
}

.logout-button:hover {
  background: rgba(255, 255, 255, 0.1);
}

@media (max-width: 760px) {
  .side-banner {
    width: 100%;
    height: auto;
    flex-basis: auto;
    overflow: visible;
    gap: 14px;
  }

  .side-nav {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    padding: 0;
  }
}
</style>
