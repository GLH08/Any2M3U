<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '@/api'
import type { SourceOut } from '@/types'

const props = defineProps<{ modelValue: Partial<SourceOut> | null }>()
const emit = defineEmits<{ (e: 'submit', v: any): void; (e: 'cancel'): void }>()

const form = ref<any>({
  name: '',
  type: 'local',
  config: { path: '' },
  group_by_dir: false,
  refresh_cron: '',
  enabled: true
})
onMounted(() => {
  if (props.modelValue) Object.assign(form.value, props.modelValue)
})

function submit() { emit('submit', form.value) }
</script>
<template>
  <el-form label-width="140px">
    <el-form-item label="Name"><el-input v-model="form.name" /></el-form-item>
    <el-form-item label="Type">
      <el-radio-group v-model="form.type">
        <el-radio value="local">Local</el-radio>
        <el-radio value="webdav">WebDAV</el-radio>
      </el-radio-group>
    </el-form-item>
    <template v-if="form.type === 'local'">
      <el-form-item label="Path (in container)"><el-input v-model="form.config.path" placeholder="/media/Movies" /></el-form-item>
    </template>
    <template v-else>
      <el-form-item label="URL"><el-input v-model="form.config.url" placeholder="https://dav.example.com" /></el-form-item>
      <el-form-item label="Username"><el-input v-model="form.config.username" /></el-form-item>
      <el-form-item label="Password"><el-input v-model="form.config.password" type="password" show-password /></el-form-item>
      <el-form-item label="Root path"><el-input v-model="form.config.root_path" placeholder="/Media" /></el-form-item>
      <el-form-item label="Verify TLS"><el-switch v-model="form.config.verify_tls" /></el-form-item>
    </template>
    <el-form-item label="Group by subdir">
      <el-switch v-model="form.group_by_dir" />
    </el-form-item>
    <el-form-item label="Refresh cron">
      <el-input v-model="form.refresh_cron" placeholder="e.g. 0 */6 * * *  (leave blank for manual)" />
    </el-form-item>
    <el-form-item label="Enabled"><el-switch v-model="form.enabled" /></el-form-item>
    <el-form-item>
      <el-button @click="$emit('cancel')">Cancel</el-button>
      <el-button type="primary" @click="submit">Save</el-button>
    </el-form-item>
  </el-form>
</template>
