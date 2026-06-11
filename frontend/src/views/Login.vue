<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const username = ref('admin')
const password = ref('')
const loading = ref(false)

async function submit() {
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    router.push((route.query.next as string) || '/')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div style="display:flex; height:100vh; align-items:center; justify-content:center">
    <el-card header="Any2M3U — Login" style="width: 360px">
      <el-form @submit.prevent="submit">
        <el-form-item label="Username"><el-input v-model="username" /></el-form-item>
        <el-form-item label="Password"><el-input v-model="password" type="password" show-password /></el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" style="width:100%">Login</el-button>
      </el-form>
    </el-card>
  </div>
</template>
