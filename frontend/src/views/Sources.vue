<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '@/api'
import SourceForm from '@/components/SourceForm.vue'
import type { SourceOut } from '@/types'

const list = ref<SourceOut[]>([])
const show = ref(false)
const editing = ref<Partial<SourceOut> | null>(null)

async function refresh() {
  const r = await api.get('/api/sources')
  list.value = r.data
}
onMounted(refresh)

function add() { editing.value = null; show.value = true }
function edit(s: SourceOut) { editing.value = s; show.value = true }
async function save(form: any) {
  if (editing.value?.id) await api.patch(`/api/sources/${editing.value.id}`, form)
  else await api.post('/api/sources', form)
  show.value = false; await refresh()
}
async function remove(s: SourceOut) {
  await api.delete(`/api/sources/${s.id}`)
  await refresh()
}
async function test(s: SourceOut) {
  const r = await api.post(`/api/sources/${s.id}/test`)
  alert(r.data.ok ? `OK in ${r.data.latency_ms} ms` : `FAILED: ${r.data.error}`)
}
</script>
<template>
  <div>
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px">
      <h2>Sources</h2>
      <el-button type="primary" @click="add">Add source</el-button>
    </div>
    <el-table :data="list" border>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="Name" />
      <el-table-column prop="type" label="Type" width="100" />
      <el-table-column prop="last_scan_status" label="Last scan" width="120" />
      <el-table-column label="Actions" width="360">
        <template #default="{ row }">
          <el-button size="small" @click="test(row as SourceOut)">Test</el-button>
          <el-button size="small" @click="edit(row as SourceOut)">Edit</el-button>
          <el-button size="small" type="danger" @click="remove(row as SourceOut)">Delete</el-button>
          <el-button size="small" @click="$router.push(`/sources/${(row as SourceOut).id}`)">Open</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="show" title="Source" width="640px">
      <SourceForm :model-value="editing" @submit="save" @cancel="show=false" />
    </el-dialog>
  </div>
</template>
