<script setup lang="ts">
import { onMounted, ref } from 'vue'

const props = defineProps<{ modelValue: any }>()
const emit = defineEmits<{ (e: 'submit', v: any): void; (e: 'cancel'): void }>()

const DEFAULT_TPL = '#EXTINF:-1 group-title="<group>",<title>\n<base>/proxy?token=<t>&id=<eid>'

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
  <el-form label-width="160px" label-position="right">
    <el-form-item label="规则名称">
      <el-input v-model="form.name" placeholder="如：电影" />
    </el-form-item>
    <el-form-item label="包含后缀 (csv)">
      <el-input v-model="form.include_exts" placeholder="mp4,mkv,ts" />
      <div style="color:var(--ink-500); font-size:12px; margin-top:4px">留空则匹配所有后缀</div>
    </el-form-item>
    <el-form-item label="排除关键词 (csv)">
      <el-input v-model="form.exclude_keywords" placeholder="sample,trailer" />
      <div style="color:var(--ink-500); font-size:12px; margin-top:4px">路径包含任一关键词则排除</div>
    </el-form-item>
    <el-form-item label="包含路径前缀 (csv)">
      <el-input v-model="form.include_paths" placeholder="Movies/,Shows/" />
      <div style="color:var(--ink-500); font-size:12px; margin-top:4px">留空则包含所有路径</div>
    </el-form-item>
    <el-form-item label="分组标题 (group-title)">
      <el-input v-model="form.group_title" placeholder="电影 / 剧集 / 直播 ..." />
    </el-form-item>
    <el-form-item label="封面 URL 前缀 (logo_dir)">
      <el-input v-model="form.logo_dir" placeholder="留空则不输出封面" />
      <div style="color:var(--ink-500); font-size:12px; margin-top:4px">
        需填<strong>完整 URL 前缀</strong>（如 <code>https://cdn/posters</code>），并在模板里加 <code>tvg-logo="&lt;logo&gt;"</code>。
        <code>&lt;logo&gt;</code> 展开为 <code>前缀/&lt;文件名&gt;.jpg</code>。本服务不托管封面图。
      </div>
    </el-form-item>
    <el-form-item label="M3U 模板">
      <el-input v-model="form.tpl" type="textarea" :rows="5" />
      <div style="color:var(--ink-500); font-size:12px; margin-top:4px">
        占位符：<code>&lt;base&gt;</code> 服务地址、<code>&lt;title&gt;</code> 标题、
        <code>&lt;group&gt;</code> 分组、<code>&lt;logo&gt;</code> 封面（需 logo_dir 填完整 URL 前缀）、
        <code>&lt;t&gt;</code> token、<code>&lt;eid&gt;</code> 条目ID、<code>&lt;sid&gt;</code> 源ID
      </div>
    </el-form-item>
    <el-form-item label="启用">
      <el-switch v-model="form.enabled" />
    </el-form-item>
    <el-form-item>
      <el-button @click="$emit('cancel')">取消</el-button>
      <el-button type="primary" @click="submit">保存</el-button>
    </el-form-item>
  </el-form>
</template>
