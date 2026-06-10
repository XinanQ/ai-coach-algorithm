<template>
  <div class="app-shell">
    <Sidebar />

    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import Sidebar from '../components/Sidebar.vue'
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
  overflow: auto;
  padding: 24px;
  box-sizing: border-box;
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
}
</style>
