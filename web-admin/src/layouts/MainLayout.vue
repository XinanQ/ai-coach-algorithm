<template>
  <div class="app-shell">
    <Sidebar />

    <main class="main-content">
      <div class="top-bar">
        <div class="bar-user-info">
          <span class="bar-name">{{ currentUser?.name || '用户' }}</span>
          <span class="bar-meta">{{ currentUser?.roleName }} · {{ currentUser?.organization }}</span>
        </div>

        <div class="user-avatar-wrapper">
          <button class="avatar-btn" type="button" @click.stop="showUserMenu = !showUserMenu">
            <span class="avatar-circle">{{ userInitial }}</span>
          </button>

          <div v-if="showUserMenu" class="user-menu-panel">
            <div class="menu-header">
              <span class="menu-name">{{ currentUser?.name || '用户' }}</span>
              <span class="menu-role">{{ currentUser?.roleName || '' }}</span>
            </div>
            <dl class="menu-info">
              <div><dt>账号</dt><dd>{{ currentUser?.username || '—' }}</dd></div>
              <div><dt>机构</dt><dd>{{ currentUser?.organization || '—' }}</dd></div>
              <div><dt>数据范围</dt><dd>{{ currentUser?.dataScope || '—' }}</dd></div>
            </dl>
            <button class="logout-btn-danger" type="button" @click="handleLogout">
              登出
            </button>
          </div>
        </div>
      </div>

      <div class="scroll-area">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import { clearCurrentUser, getCurrentUser } from '../auth/permissions'
import Sidebar from '../components/Sidebar.vue'

const router = useRouter()
const currentUser = computed(() => getCurrentUser())
const showUserMenu = ref(false)

const userInitial = computed(() => {
  const name = currentUser.value?.name || ''
  return name.charAt(0).toUpperCase() || 'U'
})

function handleLogout() {
  clearCurrentUser()
  router.push('/login')
}

function handleClickOutside(e) {
  const wrapper = e.target.closest('.user-avatar-wrapper')
  if (!wrapper) showUserMenu.value = false
}

onMounted(() => document.addEventListener('click', handleClickOutside))
onBeforeUnmount(() => document.removeEventListener('click', handleClickOutside))
</script>

<style scoped>
.app-shell {
  height: 100svh;
  display: flex;
  align-items: stretch;
  overflow: hidden;
  background: #f6f8fb;
  color: #1f2937;
}

.main-content {
  flex: 1 1 auto;
  min-width: 0;
  height: 100svh;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

.scroll-area {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 24px;
}

.top-bar {
  flex-shrink: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 52px;
  padding: 0 20px;
  background: rgba(255, 255, 255, 0.45);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(229, 231, 235, 0.6);
}

.bar-user-info {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
}

.bar-name {
  font-size: 15px;
  font-weight: 700;
  color: #111827;
  white-space: nowrap;
}

.bar-meta {
  font-size: 12px;
  color: #6b7280;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-avatar-wrapper {
  position: relative;
}

.avatar-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  outline: none;
}

.avatar-circle {
  display: block;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #0f766e, #14b8a6);
  color: #fff;
  font-size: 16px;
  font-weight: 700;
  line-height: 40px;
  text-align: center;
  box-shadow: 0 2px 10px rgba(15, 118, 110, 0.35);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  user-select: none;
}

.avatar-btn:hover .avatar-circle {
  transform: scale(1.08);
  box-shadow: 0 4px 16px rgba(15, 118, 110, 0.45);
}

.user-menu-panel {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 260px;
  border-radius: 12px;
  background: #fff;
  box-shadow:
    0 16px 48px rgba(0, 0, 0, 0.18),
    0 4px 12px rgba(0, 0, 0, 0.08);
  border: 1px solid #e5e7eb;
  overflow: hidden;
  animation: menuSlideIn 0.2s ease-out;
}

@keyframes menuSlideIn {
  from {
    opacity: 0;
    transform: translateY(-6px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.menu-header {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 16px 16px 4px;
}

.menu-name {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}

.menu-role {
  font-size: 12px;
  color: #0f766e;
  background: #ecfdf5;
  padding: 1px 8px;
  border-radius: 999px;
}

.menu-info {
  margin: 10px 16px 0;
  display: grid;
  gap: 8px;
}

.menu-info div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f3f4f6;
}

.menu-info dt {
  color: #9ca3af;
  font-size: 12px;
  white-space: nowrap;
}

.menu-info dd {
  color: #374151;
  font-size: 12px;
  font-weight: 600;
  text-align: right;
  word-break: break-all;
  margin: 0;
}

.logout-btn-danger {
  width: 100%;
  height: 38px;
  margin-top: 12px;
  border: none;
  border-radius: 0 0 11px 11px;
  background: #dc2626;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease;
}

.logout-btn-danger:hover {
  background: #b91c1c;
}

@media (max-width: 760px) {
  .app-shell {
    height: auto;
    min-height: 100svh;
    display: grid;
    overflow: visible;
  }

  .main-content {
    height: auto;
    overflow: visible;
  }

  .scroll-area {
    padding: 16px;
  }
}
</style>