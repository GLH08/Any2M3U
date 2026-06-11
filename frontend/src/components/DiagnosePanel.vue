<script setup lang="ts">
/**
 * DiagnosePanel — issues a single PROPFIND and shows raw request/response
 * so the user can verify their WebDAV config without running a full scan.
 */
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Connection, VideoPlay } from '@element-plus/icons-vue'
import { api } from '@/api'

const props = defineProps<{ sourceId: number }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'rescanned'): void }>()

const loading = ref(false)
const result = ref<any>(null)

async function run() {
  loading.value = true
  result.value = null
  try {
    const r = await api.post(`/api/sources/${props.sourceId}/diagnose`)
    result.value = r.data
  } catch (e: any) {
    result.value = { ok: false, error: e?.response?.data?.detail || e?.message || '请求失败' }
  } finally {
    loading.value = false
  }
}

async function rescan() {
  await api.post(`/api/sources/${props.sourceId}/scan`)
  ElMessage.success('已触发扫描')
  emit('rescanned')
  setTimeout(() => emit('close'), 600)
}

onMounted(run)
</script>

<template>
  <div>
    <el-alert type="info" :closable="false" style="margin-bottom:16px">
      对媒体源根目录发起一次 PROPFIND 请求，查看上游实际响应。用来判断
      URL / 用户名 / 密码 / root_path 是否正确。
    </el-alert>

    <div style="margin-bottom:16px; display:flex; gap:8px">
      <el-button :icon="Refresh" :loading="loading" @click="run">重新诊断</el-button>
      <el-button :icon="VideoPlay" type="primary" :disabled="!result?.parsed_entries?.length" @click="rescan">
        触发完整扫描
      </el-button>
    </div>

    <div v-if="result?.error" class="diag-block err">{{ result.error }}</div>

    <div v-if="result">
      <div class="diag-section">
        <h4>请求</h4>
        <div class="diag-block">
{{ result.request?.method }} {{ result.request?.url }}
Depth: {{ result.request?.headers?.Depth }}
Authorization: {{ result.request?.headers?.Authorization }}
        </div>
      </div>

      <div class="diag-section">
        <h4>响应 <span v-if="result.response_status" :class="result.ok ? 'ok' : 'err'">HTTP {{ result.response_status }} ({{ result.latency_ms }} ms)</span></h4>
        <el-table v-if="result.parsed_entries?.length" :data="result.parsed_entries" size="small" border>
          <el-table-column label="类型" width="80">
            <template #default="{ row }">
              <el-tag v-if="row.is_dir" type="warning" size="small">目录</el-tag>
              <el-tag v-else type="success" size="small">文件</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="path" label="路径" />
          <el-table-column label="大小" width="120">
            <template #default="{ row }">
              <span v-if="!row.is_dir">{{ (row.size/1024).toFixed(1) }} KB</span>
              <span v-else>—</span>
            </template>
          </el-table-column>
        </el-table>
        <div v-else-if="result.ok" class="empty" style="padding:20px">
          <p>解析成功但根目录为空。</p>
          <p style="color:var(--ink-500); font-size:12px">
            可能原因：root_path 指向了空目录，或服务器对 Depth:1 不支持。<br>
            尝试调整 root_path，或将「按子目录分组」关闭后用扫描再试。
          </p>
        </div>
        <div v-if="result.response_body" class="diag-section" style="margin-top:16px">
          <h4>原始响应 (前 8 KB)</h4>
          <div class="diag-block">{{ result.response_body }}</div>
        </div>
      </div>
    </div>
  </div>
</template>
