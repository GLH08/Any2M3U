<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { api } from '@/api'
import RuleForm from '@/components/RuleForm.vue'
import ScanProgress from '@/components/ScanProgress.vue'
import type { SourceOut, RuleOut } from '@/types'

const props = defineProps<{ id: string | number }>()
const source = ref<SourceOut | null>(null)
const rules = ref<RuleOut[]>([])
const show = ref(false)
const editing = ref<any>(null)
const baseUrl = ref('')

async function refresh() {
  const r = await api.get(`/api/sources/${props.id}`)
  source.value = r.data
  const rr = await api.get(`/api/sources/${props.id}/rules`)
  rules.value = rr.data
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
  show.value = false; await refresh()
}
async function delRule(r: RuleOut) {
  await api.delete(`/api/rules/${r.id}`); await refresh()
}
async function scan() {
  await api.post(`/api/sources/${props.id}/scan`)
}
const m3uUrl = (rid: number) => `${baseUrl.value}/m3u/rule/${rid}?token=<token>`
</script>
<template>
  <div v-if="source">
    <h2>{{ source.name }} <el-tag size="small">{{ source.type }}</el-tag></h2>
    <el-card>
      <ScanProgress :source-id="Number(id)" />
      <div style="margin-top:8px"><el-button @click="scan" type="primary">Scan now</el-button></div>
    </el-card>
    <h3>Rules</h3>
    <el-button @click="addRule" type="primary" size="small">Add rule</el-button>
    <el-table :data="rules" border style="margin-top:8px">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="Name" />
      <el-table-column prop="include_exts" label="Exts" />
      <el-table-column prop="group_title" label="Group" />
      <el-table-column label="M3U URL">
        <template #default="{ row }">
          <code>{{ m3uUrl(row.id) }}</code>
        </template>
      </el-table-column>
      <el-table-column label="Actions" width="200">
        <template #default="{ row }">
          <el-button size="small" @click="editRule(row as RuleOut)">Edit</el-button>
          <el-button size="small" type="danger" @click="delRule(row as RuleOut)">Delete</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="show" title="Rule" width="720px">
      <RuleForm :model-value="editing" @submit="saveRule" @cancel="show=false" />
    </el-dialog>
  </div>
</template>
