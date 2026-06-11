<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const items = computed(() => [
  { path: '/', label: 'Dashboard' },
  { path: '/sources', label: 'Sources' },
  { path: '/rules', label: 'Rules' },
  { path: '/tokens', label: 'Tokens' },
  { path: '/settings', label: 'Settings' }
])
async function logout() {
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <el-container v-if="auth.user" style="height: 100vh">
    <el-aside width="200px" style="background: #001529; color: #fff; padding: 16px 0">
      <h3 style="color:#fff; text-align:center">Any2M3U</h3>
      <el-menu :router="true" background-color="#001529" text-color="#fff" active-text-color="#409EFF">
        <el-menu-item v-for="i in items" :key="i.path" :index="i.path">{{ i.label }}</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header style="display:flex; align-items:center; justify-content:flex-end; gap:12px; border-bottom:1px solid #eee">
        <span>{{ auth.user.username }}</span>
        <el-button size="small" @click="logout">Logout</el-button>
      </el-header>
      <el-main><router-view /></el-main>
    </el-container>
  </el-container>
  <router-view v-else />
</template>
