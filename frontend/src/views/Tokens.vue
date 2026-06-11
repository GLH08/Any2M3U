<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Key, Plus, CopyDocument } from '@element-plus/icons-vue'
import { api } from '@/api'

const list = ref<any[]>([])
const newName = ref('')
const lastCreated = ref<{ name: string; token: string } | null>(null)

async function refresh() {
  try { list.value = (await api.get('/api/tokens')).data } catch (e) { /* ignore */ }
}
onMounted(refresh)

async function create() {
  if (!newName.value) {
    ElMessage.warning('请填写令牌名称')
    return
  }
  const r = await api.post('/api/tokens', { name: newName.value })
  lastCreated.value = { name: r.data.name, token: r.data.token }
  newName.value = ''
  ElMessage.success('已创建，请立即复制令牌')
  await refresh()
}

async function revoke(t: any) {
  await ElMessageBox.confirm(`确定吊销令牌「${t.name}」？使用此令牌的播放器将无法继续拉取。`, '吊销确认', { type: 'warning' })
  await api.delete(`/api/tokens/${t.id}`)
  ElMessage.success('已吊销')
  await refresh()
}

async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch {}
}

function fmtTime(s: string | null) {
  return s ? s.slice(0, 19).replace('T', ' ') : '—'
}
</script>
<template>
  <div>
    <h1 class="page-title">
      <span>拉取令牌</span>
      <small>播放器订阅 M3U 时使用的长期凭证</small>
    </h1>

    <div v-if="lastCreated" class="token-box">
      <div class="label">⚠️ 请立即复制 — 此令牌只显示一次</div>
      <div class="val">{{ lastCreated.token }}</div>
      <el-button size="small" type="primary" :icon="CopyDocument" style="margin-top:8px" @click="copy(lastCreated.token)">
        复制令牌
      </el-button>
    </div>

    <div style="display:flex; gap:12px; margin-bottom:16px">
      <el-input v-model="newName" placeholder="令牌名称（如：客厅电视）" style="max-width:300px" @keyup.enter="create" />
      <el-button type="primary" :icon="Plus" @click="create">创建令牌</el-button>
    </div>

    <div v-if="list.length === 0" class="empty">
      <el-icon style="font-size:48px; color:var(--ink-300)"><Key /></el-icon>
      <h3>还没有令牌</h3>
      <p>创建一个令牌，把它附在 M3U 链接的 <code>?token=</code> 参数中</p>
    </div>

    <el-table v-else :data="list" border>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="名称" min-width="140" />
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="最近使用" width="170">
        <template #default="{ row }">{{ fmtTime(row.last_used_at) }}</template>
      </el-table-column>
      <el-table-column label="过期时间" width="170">
        <template #default="{ row }">{{ row.expires_at ? fmtTime(row.expires_at) : '永不过期' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.revoked" type="danger" size="small">已吊销</el-tag>
          <el-tag v-else type="success" size="small">有效</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="110" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="danger" :disabled="row.revoked" @click="revoke(row)">吊销</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>
