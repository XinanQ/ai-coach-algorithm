<template>
  <aside class="side-banner">
    <div class="brand-area">
      <h2>金融业务绩效管理系统</h2>
      <p>Finance Performance</p>
    </div>

    <div v-if="currentUser" class="user-card">
      <strong>{{ currentUser.name || '未登录用户' }}</strong>
      <span>
    {{ currentUser.position || currentUser.roleName || '未设置职位' }}
    ·
    {{ currentUser.organizationName || currentUser.organization || '未设置机构' }}
      </span>
    </div>

    <nav class="side-nav">
      <div
        v-for="item in visibleMenus"
        :key="item.path"
        class="nav-item"
        :class="{ 'has-children': item.children }"
      >
        <router-link :to="item.path">
          {{ item.label }}
        </router-link>
        <div v-if="item.children" class="dropdown-menu">
          <router-link
            v-for="child in item.children"
            :key="child.path"
            :to="child.path"
            class="dropdown-item"
          >
            {{ child.label }}
          </router-link>
        </div>
      </div>
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

.nav-item {
  position: relative;
}

.nav-item.has-children:hover .dropdown-menu {
  opacity: 1;
  visibility: visible;
  max-height: 300px;
  transform: translateY(0) scale(1);
}

.dropdown-menu {
  position: absolute;
  left: 0;
  top: 100%;
  min-width: 140px;
  background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4), 0 2px 6px rgba(0, 0, 0, 0.2);
  padding: 8px 0;
  opacity: 0;
  visibility: hidden;
  max-height: 0;
  transform: translateY(-8px) scale(0.96);
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 10;
  margin-top: 8px;
  overflow: hidden;
}

.dropdown-item {
  display: block;
  padding: 10px 18px;
  color: #9ca3af;
  text-decoration: none;
  font-size: 12px;
  white-space: nowrap;
  transition: all 0.25s ease;
  transform: translateX(-8px);
  opacity: 0;
  position: relative;
}

.nav-item.has-children:hover .dropdown-item {
  transform: translateX(0);
  opacity: 1;
}

.dropdown-item:nth-child(1) { transition-delay: 0.05s; }
.dropdown-item:nth-child(2) { transition-delay: 0.1s; }
.dropdown-item:nth-child(3) { transition-delay: 0.15s; }
.dropdown-item:nth-child(4) { transition-delay: 0.2s; }

.dropdown-item:hover,
.dropdown-item.router-link-active {
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  padding-left: 24px;
}

.side-nav a {
  padding: 10px 12px;
  border-radius: 6px;
  color: #d1d5db;
  text-decoration: none;
  font-size: 15px;
  display: block;
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
