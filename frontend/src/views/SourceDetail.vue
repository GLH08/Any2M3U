<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Connection, Document, CopyDocument } from '@element-plus/icons-vue'
import { api } from '@/api'
import RuleForm from '@/components/RuleForm.vue'
import ScanProgress from '@/components/ScanProgress.vue'
import type { SourceOut, RuleOut } from '@/types'

const props = defineProps<{ id: string | number }>()
const source = ref<SourceOut | null>(null)
const rules = ref<RuleOut[]>([])
const tokens = ref<any[]>([])
const show = ref(false)
const editing = ref<any>(null)
const baseUrl = ref('')

async function refresh() {
  const r = await api.get(`/api/sources/${props.id}`)
  source.value = r.data
  const rr = await api.get(`/api/sources/${props.id}/rules`)
  rules.value = rr.data
  const tk = await api.get('/api/tokens')
  tokens.value = tk.data.filter((t: any) => !t.revoked)
}
onMounted(async () => {
  await refresh()
  baseUrl.value = window.location.origin
})

function addRule() { editing.value = null; show.value = true }
function editRule(r: RuleOut) { editing.value = r; show.value = true }
async function saveRule(form: any) {
  if (editing.value?.id) await api.patch(`/api/rules/${editing.value.id}`, form)
  else await api.post(`/api/sources/${props.id}/rules`, form)
  ElMessage.success('已保存')
  show.value = false; await refresh()
}
async function delRule(r: RuleOut) {
  await ElMessageBox.confirm(`确定删除规则「${r.name}」？`, '确认', { type: 'warning' })
  await api.delete(`/api/rules/${r.id}`)
  ElMessage.success('已删除')
  await refresh()
}

function m3uUrl(rid: number, token: string) {
  return `${baseUrl.value}/m3u/rule/${rid}?token=${token}`
}

async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch { /* ignore */ }
}
</script>
<template>
  <div v-if="source">
    <h1 class="page-title">
      <span>{{ source.name }}</span>
      <el-tag :type="source.type === 'webdav' ? 'warning' : 'success'" effect="dark">
        {{ source.type === 'webdav' ? 'WebDAV' : '本地' }}
      </el-tag>
    </h1>

    <el-card style="margin-bottom:16px">
      <ScanProgress :source-id="Number(id)" />
    </el-card>

    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px">
      <h2 style="margin:0; font-size:18px">订阅规则</h2>
      <el-button type="primary" :icon="Plus" @click="addRule">添加规则</el-button>
    </div>

    <div v-if="rules.length === 0" class="empty">
      <el-icon style="font-size:48px; color:var(--ink-300)"><Connection /></el-icon>
      <h3>还没有规则</h3>
      <p>规则定义了如何从该媒体源生成 M3U 订阅</p>
    </div>

    <el-alert
      v-if="rules.length > 0"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom:12px"
      title="订阅链接含令牌，等同于密码"
      description="下方 M3U 链接的 ?token=… 是访问凭证，请勿公开分享。如需作废，请到「拉取令牌」页吊销。"
    />

    <el-table v-if="rules.length > 0" :data="rules" border>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="规则" min-width="120" />
      <el-table-column label="后缀" width="120">
        <template #default="{ row }">
          <span v-if="row.include_exts" style="font-size:12px">{{ row.include_exts }}</span>
          <span v-else style="color:var(--ink-400)">全部</span>
        </template>
      </el-table-column>
      <el-table-column label="分组" width="120">
        <template #default="{ row }">
          <el-tag v-if="row.group_title" size="small">{{ row.group_title }}</el-tag>
          <span v-else style="color:var(--ink-400)">—</span>
        </template>
      </el-table-column>
      <el-table-column label="M3U 订阅链接" min-width="280">
        <template #default="{ row }">
          <el-select
            v-if="tokens.length > 0"
            :model-value="tokens[0].token"
            placeholder="选择 Token"
            size="small"
            style="width:200px; margin-right:8px"
            @change="(t: string) => copy(m3uUrl(row.id, t))"
          >
            <el-option v-for="t in tokens" :key="t.id" :label="t.name" :value="t.token" />
          </el-select>
          <el-button size="small" :icon="CopyDocument" @click="copy(m3uUrl(row.id, tokens[0]?.token || ''))">
            复制
          </el-button>
          <div class="m3u-url" style="margin-top:6px">{{ m3uUrl(row.id, tokens[0]?.token || '⟨需要 Token⟩') }}</div>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button size="small" :icon="Edit" @click="editRule(row as RuleOut)">编辑</el-button>
          <el-button size="small" :icon="Delete" type="danger" @click="delRule(row as RuleOut)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="show" :title="editing?.id ? '编辑规则' : '添加规则'" width="780px">
      <RuleForm :model-value="editing" @submit="saveRule" @cancel="show=false" />
    </el-dialog>
  </div>
</template>
