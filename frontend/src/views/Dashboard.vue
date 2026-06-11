<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '@/api'

const status = ref<any>(null)
onMounted(async () => {
  try {
    const r = await api.get('/api/scan/status')
    status.value = r.data
  } catch (e) { /* ignore */ }
})
</script>
<template>
  <div>
    <h2>Dashboard</h2>
    <el-row :gutter="16" v-if="status">
      <el-col :span="8"><el-card>Total sources: <b>{{ status.sources_total }}</b></el-card></el-col>
      <el-col :span="8"><el-card>Scanning now: <b>{{ status.sources_scanning }}</b></el-card></el-col>
      <el-col :span="8"><el-card>Last full pass: <b>{{ status.last_full_pass_at || '—' }}</b></el-card></el-col>
    </el-row>
    <p v-else>Loading…</p>
  </div>
</template>
