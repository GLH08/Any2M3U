<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { Plus, Delete, Folder, Link, Edit, Search, QuestionFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '@/api'
import SourceForm from '@/components/SourceForm.vue'
import DiagnosePanel from '@/components/DiagnosePanel.vue'
import type { SourceOut } from '@/types'

const list = ref<SourceOut[]>([])
const show = ref(false)
const editing = ref<Partial<SourceOut> | null>(null)
const showDiag = ref(false)
const diagId = ref<number | null>(null)
const filter = ref('')

async function refresh() {
  const r = await api.get('/api/sources')
  list.value = r.data
}
onMounted(refresh)
watch(filter, () => {})

function add() { editing.value = null; show.value = true }
function edit(s: SourceOut) { editing.value = s; show.value = true }
async function save(form: any) {
  if (editing.value?.id) await api.patch(`/api/sources/${editing.value.id}`, form)
  else await api.post('/api/sources', form)
  ElMessage.success('已保存')
  show.value = false; await refresh()
}
async function remove(s: SourceOut) {
  await ElMessageBox.confirm(`确定删除媒体源「${s.name}」？关联的规则和扫描缓存也会被删除。`, '删除确认', { type: 'warning' })
  await api.delete(`/api/sources/${s.id}`)
  ElMessage.success('已删除')
  await refresh()
}
async function test(s: SourceOut) {
  const r = await api.post(`/api/sources/${s.id}/test`)
  if (r.data.ok) ElMessage.success(`连接成功 (${r.data.latency_ms} ms)`)
  else ElMessage.error(`连接失败: ${r.data.error}`)
}
function diagnose(s: SourceOut) { diagId.value = s.id; showDiag.value = true }
async function triggerScan(s: SourceOut) {
  await api.post(`/api/sources/${s.id}/scan`)
  ElMessage.success('已触发扫描')
}

const filtered = () => {
  if (!filter.value) return list.value
  const q = filter.value.toLowerCase()
  return list.value.filter(s => s.name.toLowerCase().includes(q) || s.type.includes(q))
}
</script>

<template>
  <div>
    <div class="page-title">
      <span>媒体源</span>
      <small>WebDAV 远程或本地目录</small>
    </div>

    <div v-if="list.length === 0" class="empty">
      <el-icon style="font-size:48px; color:var(--ink-300)"><Folder /></el-icon>
      <h3>还没有媒体源</h3>
      <p>添加 WebDAV 服务器或本地目录来开始</p>
      <el-button type="primary" :icon="Plus" @click="add">添加媒体源</el-button>
    </div>

    <template v-else>
      <div style="display:flex; gap:12px; margin-bottom:16px">
        <el-input v-model="filter" placeholder="按名称搜索..." :prefix-icon="Search" clearable style="max-width:300px" />
        <el-button type="primary" :icon="Plus" @click="add">添加媒体源</el-button>
      </div>

      <el-table :data="filtered()" border>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column label="名称" min-width="180">
          <template #default="{ row }">
            <router-link :to="`/sources/${row.id}`" style="color:var(--brand-700); font-weight:500; text-decoration:none">
              {{ row.name }}
            </router-link>
            <div v-if="row.last_error" style="color:var(--danger); font-size:11px; margin-top:2px; max-width:260px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap" :title="row.last_error">
              {{ row.last_error }}
            </div>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.type === 'webdav' ? 'warning' : 'success'" size="small">
              <el-icon style="vertical-align:-2px"><Link v-if="row.type==='webdav'"/><Folder v-else/></el-icon>
              {{ row.type === 'webdav' ? 'WebDAV' : '本地' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.last_scan_status === 'success'" type="success" size="small">扫描成功</el-tag>
            <el-tag v-else-if="row.last_scan_status === 'failed'" type="danger" size="small">扫描失败</el-tag>
            <el-tag v-else-if="row.last_scan_status === 'running'" type="warning" size="small">扫描中</el-tag>
            <el-tag v-else size="small" type="info">未扫描</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_scan_at" label="最近扫描" width="180">
          <template #default="{ row }">
            <span v-if="row.last_scan_at" style="font-size:12px; color:var(--ink-600)">{{ row.last_scan_at.slice(0,19).replace('T',' ') }}</span>
            <span v-else style="color:var(--ink-400)">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="500" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="$router.push(`/sources/${row.id}`)">订阅规则</el-button>
            <el-button size="small" :icon="QuestionFilled" @click="diagnose(row as SourceOut)">诊断</el-button>
            <el-button size="small" :icon="Search" @click="test(row as SourceOut)">测试</el-button>
            <el-button size="small" :icon="Edit" @click="edit(row as SourceOut)">编辑</el-button>
            <el-button size="small" :icon="Delete" type="danger" @click="remove(row as SourceOut)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </template>

    <el-dialog v-model="show" :title="editing ? '编辑媒体源' : '添加媒体源'" width="680px">
      <SourceForm :model-value="editing" @submit="save" @cancel="show=false" />
    </el-dialog>

    <el-drawer v-model="showDiag" title="WebDAV 诊断" size="780px" direction="rtl">
      <DiagnosePanel v-if="diagId" :source-id="diagId" @close="showDiag=false" @rescanned="refresh" />
    </el-drawer>
  </div>
</template>
