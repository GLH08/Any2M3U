<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const oldPw = ref('')
const newPw = ref('')
async function change() {
  await auth.changePassword(oldPw.value, newPw.value)
  oldPw.value = ''; newPw.value = ''
}
</script>
<template>
  <div>
    <h2>Settings</h2>
    <el-card header="Change password" style="max-width:480px">
      <el-form @submit.prevent="change">
        <el-form-item label="Current"><el-input v-model="oldPw" type="password" show-password /></el-form-item>
        <el-form-item label="New"><el-input v-model="newPw" type="password" show-password /></el-form-item>
        <el-button type="primary" native-type="submit">Change</el-button>
      </el-form>
    </el-card>
  </div>
</template>
