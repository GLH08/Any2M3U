<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  Odometer, Folder, Connection, Key, Setting, SwitchButton,
} from '@element-plus/icons-vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const items = computed(() => [
  { path: '/', label: '仪表盘', icon: Odometer },
  { path: '/sources', label: '媒体源', icon: Folder },
  { path: '/rules', label: '订阅规则', icon: Connection },
  { path: '/tokens', label: '拉取令牌', icon: Key },
  { path: '/settings', label: '设置', icon: Setting },
])
const active = computed(() => route.path)
async function logout() {
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="app-shell" v-if="auth.user">
    <aside class="app-side">
      <div class="brand">
        <span class="dot"></span>
        <span>Any2M3U</span>
      </div>
      <nav>
        <router-link
          v-for="i in items" :key="i.path" :to="i.path"
          custom v-slot="{ navigate }"
        >
          <div class="nav-item" :class="{ active: active === i.path }" @click="navigate">
            <el-icon><component :is="i.icon" /></el-icon>
            <span>{{ i.label }}</span>
          </div>
        </router-link>
      </nav>
      <div class="user-card">
        <span>{{ auth.user.username }}</span>
        <el-button size="small" link @click="logout">
          <el-icon><SwitchButton /></el-icon> 退出
        </el-button>
      </div>
    </aside>
    <main class="app-main">
      <header class="app-header">
        <div class="crumb">Any2M3U · {{ items.find(i => i.path === active)?.label || '' }}</div>
        <el-button size="small" plain @click="logout">退出登录</el-button>
      </header>
      <div class="app-body">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>
  </div>
  <router-view v-else />
</template>
