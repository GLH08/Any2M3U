<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const oldPw = ref('')
const newPw = ref('')
const newPw2 = ref('')
const loading = ref(false)

async function change() {
  if (!oldPw.value || !newPw.value) {
    ElMessage.warning('请填写当前密码和新密码')
    return
  }
  if (newPw.value.length < 8) {
    ElMessage.warning('新密码至少 8 位')
    return
  }
  if (newPw.value !== newPw2.value) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  loading.value = true
  try {
    await auth.changePassword(oldPw.value, newPw.value)
    ElMessage.success('密码已修改')
    oldPw.value = ''; newPw.value = ''; newPw2.value = ''
  } finally {
    loading.value = false
  }
}
</script>
<template>
  <div>
    <h1 class="page-title">
      <span>设置</span>
    </h1>

    <el-card style="max-width:520px">
      <template #header>
        <div style="display:flex; align-items:center; gap:8px">
          <el-icon><Lock /></el-icon>
          <span>修改密码</span>
        </div>
      </template>
      <el-form @submit.prevent="change" label-position="top">
        <el-form-item label="当前密码">
          <el-input v-model="oldPw" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码（至少 8 位）">
          <el-input v-model="newPw" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="newPw2" type="password" show-password />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading">修改密码</el-button>
      </el-form>
    </el-card>

    <el-card style="max-width:520px; margin-top:16px">
      <template #header>使用提示</template>
      <ul style="margin:0; padding-left:18px; color:var(--ink-600); font-size:13px; line-height:2">
        <li>M3U 链接格式：<code>https://你的域名/m3u/rule/&lt;规则ID&gt;?token=&lt;令牌&gt;</code></li>
        <li>播放器（VLC / IINA / PotPlayer / Kodi）直接订阅该链接即可</li>
        <li>媒体源更新后，手动「立即扫描」或配置定时刷新（cron）</li>
        <li>公网部署务必使用 HTTPS（参见 <code>deploy/nginx.example.conf</code>）</li>
      </ul>
    </el-card>
  </div>
</template>
