<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { api } from '@/api'

const list = ref<any[]>([])
const newName = ref('')
const lastCreated = ref<{ name: string; token: string } | null>(null)
async function refresh() {
  try { list.value = (await api.get('/api/tokens')).data } catch (e) { /* ignore */ }
}
onMounted(refresh)
async function create() {
  if (!newName.value) return
  const r = await api.post('/api/tokens', { name: newName.value })
  lastCreated.value = { name: r.data.name, token: r.data.token }
  newName.value = ''
  await refresh()
}
async function revoke(t: any) {
  await ElMessageBox.confirm(`Revoke token "${t.name}"?`, 'Confirm', { type: 'warning' })
  await api.delete(`/api/tokens/${t.id}`)
  await refresh()
}
</script>
<template>
  <div>
    <h2>Pull tokens</h2>
    <el-card v-if="lastCreated" style="margin-bottom:16px">
      <p><b>Copy this token now — it won't be shown again.</b></p>
      <code style="word-break:break-all; user-select:all">{{ lastCreated.token }}</code>
    </el-card>
    <el-input v-model="newName" placeholder="Token name (e.g. Living Room TV)" style="width:300px" />
    <el-button type="primary" @click="create">Create</el-button>
    <el-table :data="list" border style="margin-top:12px">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="Name" />
      <el-table-column prop="created_at" label="Created" />
      <el-table-column prop="last_used_at" label="Last used" />
      <el-table-column prop="expires_at" label="Expires" />
      <el-table-column prop="revoked" label="Revoked" width="100" />
      <el-table-column label="Actions" width="120">
        <template #default="{ row }">
          <el-button size="small" type="danger" :disabled="row.revoked" @click="revoke(row)">Revoke</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>
