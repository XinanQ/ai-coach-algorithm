<template>
  <router-view v-if="isPublicPage" />
  <MainLayout v-else />
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import MainLayout from './layouts/MainLayout.vue'

const route = useRoute()

const isPublicPage = computed(() => Boolean(route.meta?.public))
</script>
