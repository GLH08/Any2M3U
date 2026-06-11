<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const username = ref('admin')
const password = ref('')
const loading = ref(false)
const errorMsg = ref('')

async function submit() {
  if (!username.value || !password.value) {
    errorMsg.value = '请填写用户名和密码'
    return
  }
  loading.value = true
  errorMsg.value = ''
  try {
    await auth.login(username.value, password.value)
    ElMessage.success('登录成功')
    router.push((route.query.next as string) || '/')
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.detail || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-bg">
    <div class="auth-card">
      <h1>
        <span style="width:12px; height:12px; border-radius:50%; background:linear-gradient(135deg,#06b6d4,#0e7490); display:inline-block;"></span>
        Any2M3U
      </h1>
      <div class="sub">将 WebDAV / 本地媒体转换为 M3U 订阅</div>

      <el-alert v-if="errorMsg" type="error" :closable="false" :title="errorMsg" style="margin-bottom:16px" />

      <el-form @submit.prevent="submit" label-position="top">
        <el-form-item label="用户名">
          <el-input v-model="username" size="large" :prefix-icon="'User'" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="password" type="password" show-password size="large" />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" size="large" style="width:100%; margin-top:8px">
          登录
        </el-button>
      </el-form>

      <div style="text-align:center; margin-top:20px; color:var(--ink-500); font-size:12px">
        首次启动？初始密码见容器日志或 <code>data/INITIAL_PASSWORD.txt</code>
      </div>
    </div>
  </div>
</template>
