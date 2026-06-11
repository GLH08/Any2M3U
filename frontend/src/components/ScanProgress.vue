<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed } from 'vue'
import { api } from '@/api'
import { VideoPlay, CircleClose, Document } from '@element-plus/icons-vue'

const props = defineProps<{ sourceId: number }>()
const emit = defineEmits<{ (e: 'scan'): void }>()

const status = ref<any>(null)
let timer: any = null

async function poll() {
  try {
    const r = await api.get(`/api/sources/${props.sourceId}/scan`)
    status.value = r.data
  } catch (e) { /* ignore */ }
}

async function trigger() {
  await api.post(`/api/sources/${props.sourceId}/scan`)
  poll()
}

onMounted(() => { poll(); timer = setInterval(poll, 1500) })
onUnmounted(() => clearInterval(timer))

const statusType = computed(() => {
  if (!status.value) return 'info'
  if (status.value.status === 'success') return 'success'
  if (status.value.status === 'failed') return 'danger'
  if (status.value.status === 'running') return 'warning'
  return 'info'
})

const statusLabel = computed(() => {
  if (!status.value) return '加载中'
  const m: any = {
    success: '扫描成功', failed: '扫描失败',
    running: '扫描中', idle: '未扫描', '': '未扫描',
  }
  return m[status.value.status] || status.value.status
})
</script>
<template>
  <div v-if="status" style="display:flex; align-items:center; gap:16px; flex-wrap:wrap">
    <el-tag :type="statusType" size="large" effect="dark">{{ statusLabel }}</el-tag>

    <div v-if="status.status==='running'" style="color:var(--ink-600); font-size:13px">
      已处理 <b style="color:var(--brand-700)">{{ status.progress }}</b> 个条目
    </div>
    <div v-else-if="status.status==='success'" style="color:var(--ink-600); font-size:13px">
      共 <b>{{ status.entry_count }}</b> 个文件，
      总大小 <b>{{ (status.total_bytes/1048576).toFixed(2) }} MB</b>
    </div>
    <div v-else-if="status.status==='failed'" style="color:var(--ink-600); font-size:13px">
      扫描失败
    </div>

    <el-button :icon="VideoPlay" size="small" @click="trigger" :disabled="status.status==='running'">
      立即扫描
    </el-button>

    <div v-if="status.last_error" style="flex-basis:100%; color:var(--danger); font-size:12px; background:#fef2f2; padding:8px 12px; border-radius:6px; border-left:3px solid var(--danger)">
      <el-icon><CircleClose /></el-icon> {{ status.last_error }}
    </div>
  </div>
</template>
