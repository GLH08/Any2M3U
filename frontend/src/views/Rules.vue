<script setup lang="ts">
import { onMounted, ref } from 'vue'
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
const url = (rid: number) => `${baseUrl.value}/m3u/rule/${rid}?token=<token>`
</script>
<template>
  <div>
    <h2>All rules</h2>
    <el-table :data="rules" border>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="source_name" label="Source" />
      <el-table-column prop="name" label="Name" />
      <el-table-column prop="include_exts" label="Exts" />
      <el-table-column prop="group_title" label="Group" />
      <el-table-column label="M3U URL">
        <template #default="{ row }"><code>{{ url(row.id) }}</code></template>
      </el-table-column>
    </el-table>
  </div>
</template>
