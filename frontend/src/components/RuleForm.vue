<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

const props = defineProps<{ modelValue: any }>()
const emit = defineEmits<{ (e: 'submit', v: any): void; (e: 'cancel'): void }>()

const DEFAULT_TPL = '#EXTINF:-1 tvg-logo="<base>/logo/<sid>/<logo>" group-title="<group>",<title>\n<base>/proxy?token=<t>&id=<eid>'

const form = ref<any>({
  name: '',
  include_exts: 'mp4,mkv,ts',
  exclude_keywords: '',
  include_paths: '',
  group_title: '',
  tpl: DEFAULT_TPL,
  logo_dir: '',
  enabled: true
})
onMounted(() => {
  if (props.modelValue) Object.assign(form.value, props.modelValue)
})
function submit() { emit('submit', form.value) }
</script>
<template>
  <el-form label-width="160px">
    <el-form-item label="Name"><el-input v-model="form.name" /></el-form-item>
    <el-form-item label="Include exts (csv)"><el-input v-model="form.include_exts" /></el-form-item>
    <el-form-item label="Exclude keywords (csv)"><el-input v-model="form.exclude_keywords" /></el-form-item>
    <el-form-item label="Include path prefixes (csv)"><el-input v-model="form.include_paths" /></el-form-item>
    <el-form-item label="Group title"><el-input v-model="form.group_title" /></el-form-item>
    <el-form-item label="Logo dir (subdir)"><el-input v-model="form.logo_dir" /></el-form-item>
    <el-form-item label="M3U template">
      <el-input v-model="form.tpl" type="textarea" :rows="4" />
    </el-form-item>
    <el-form-item label="Enabled"><el-switch v-model="form.enabled" /></el-form-item>
    <el-form-item>
      <el-button @click="$emit('cancel')">Cancel</el-button>
      <el-button type="primary" @click="submit">Save</el-button>
    </el-form-item>
  </el-form>
</template>
