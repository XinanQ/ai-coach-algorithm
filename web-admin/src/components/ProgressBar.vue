<template>
  <div class="progress">
    <div class="progress-track">
      <span :style="{ width: `${value}%` }"></span>
    </div>
    <strong>{{ value }}%</strong>
  </div>
</template>

<script setup>
defineProps({
  value: {
    type: Number,
    required: true
  }
})
</script>

<style scoped>
.progress {
  display: flex;
  align-items: center;
  gap: 10px;
}

.progress-track {
  width: 120px;
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: #e5e7eb;
}

.progress-track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #0f766e;
}

strong {
  min-width: 42px;
  color: #111827;
  font-size: 13px;
}
</style>
