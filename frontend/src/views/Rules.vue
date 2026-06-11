<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Connection, Folder } from '@element-plus/icons-vue'
import { api } from '@/api'
import type { RuleOut, SourceOut } from '@/types'

const rules = ref<(RuleOut & { source_name?: string })[]>([])
const baseUrl = ref('')
onMounted(async () => {
  try {
    const srcs = (await api.get('/api/sources')).data as SourceOut[]
    baseUrl.value = window.location.origin
    const all: any[] = []
    for (const s of srcs) {
      const rs = (await api.get(`/api/sources/${s.id}/rules`)).data as RuleOut[]
      for (const r of rs) all.push({ ...r, source_name: s.name })
    }
    rules.value = all
  } catch (e) { /* ignore */ }
})

async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制')
  } catch {}
}
function url(rid: number) { return `${baseUrl.value}/m3u/rule/${rid}?token=⟨你的 token⟩` }
</script>
<template>
  <div>
    <h1 class="page-title">
      <span>订阅规则</span>
      <small>所有媒体源的规则</small>
    </h1>

    <div v-if="rules.length === 0" class="empty">
      <el-icon style="font-size:48px; color:var(--ink-300)"><Connection /></el-icon>
      <h3>还没有规则</h3>
      <p>进入任意媒体源详情页添加订阅规则</p>
    </div>

    <el-table v-else :data="rules" border>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column label="媒体源" min-width="140">
        <template #default="{ row }">
          <el-icon style="vertical-align:-2px; color:var(--brand-600)"><Folder /></el-icon>
          <router-link :to="`/sources/${row.source_id}`" style="margin-left:4px; color:var(--brand-700); text-decoration:none">
            {{ row.source_name }}
          </router-link>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="规则" min-width="120" />
      <el-table-column label="后缀" width="140">
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
      <el-table-column label="M3U 链接模板" min-width="320">
        <template #default="{ row }">
          <code style="font-size:11.5px; word-break:break-all">{{ url(row.id) }}</code>
          <el-button size="small" link type="primary" @click="copy(url(row.id))" style="margin-left:8px">复制</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>
