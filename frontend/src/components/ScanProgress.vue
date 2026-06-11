<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { api } from '@/api'

const props = defineProps<{ sourceId: number }>()
const status = ref<any>(null)
let timer: any = null
async function poll() {
  try {
    const r = await api.get(`/api/sources/${props.sourceId}/scan`)
    status.value = r.data
  } catch (e) { /* ignore */ }
}
onMounted(() => { poll(); timer = setInterval(poll, 1500) })
onUnmounted(() => clearInterval(timer))
</script>
<template>
  <div v-if="status">
    <el-tag :type="status.status==='success' ? 'success' : status.status==='failed' ? 'danger' : 'info'">
      {{ status.status }}
    </el-tag>
    <div v-if="status.status==='running'">Progress: {{ status.progress }}</div>
    <div v-else>Entries: {{ status.entry_count }} ({{ (status.total_bytes/1048576).toFixed(1) }} MB)</div>
    <div v-if="status.last_error" style="color:#c00; font-size:12px">{{ status.last_error }}</div>
  </div>
</template>
