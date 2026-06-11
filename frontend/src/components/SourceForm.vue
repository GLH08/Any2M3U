<script setup lang="ts">
import { onMounted, ref } from 'vue'
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
  if (form.value.type === 'webdav' && !form.value.config) {
    form.value.config = { url: '', username: '', password: '', root_path: '/', verify_tls: true }
  }
})

function submit() { emit('submit', form.value) }
</script>
<template>
  <el-form label-width="160px" label-position="right">
    <el-form-item label="名称">
      <el-input v-model="form.name" placeholder="如：家庭影库" />
    </el-form-item>
    <el-form-item label="类型">
      <el-radio-group v-model="form.type">
        <el-radio-button value="local">本地目录</el-radio-button>
        <el-radio-button value="webdav">WebDAV</el-radio-button>
      </el-radio-group>
    </el-form-item>

    <template v-if="form.type === 'local'">
      <el-form-item label="容器内路径">
        <el-input v-model="form.config.path" placeholder="/media/Movies" />
        <div style="color:var(--ink-500); font-size:12px; margin-top:4px">
          容器内可访问的绝对路径。宿主路径通过 docker-compose 的 volumes 挂载。
        </div>
      </el-form-item>
    </template>

    <template v-else>
      <el-form-item label="服务地址 (URL)">
        <el-input v-model="form.config.url" placeholder="https://dav.example.com" />
      </el-form-item>
      <el-form-item label="用户名">
        <el-input v-model="form.config.username" />
      </el-form-item>
      <el-form-item label="密码">
        <el-input v-model="form.config.password" type="password" show-password />
      </el-form-item>
      <el-form-item label="根路径 (root_path)">
        <el-input v-model="form.config.root_path" placeholder="/dav/files/admin" />
        <div style="color:var(--ink-500); font-size:12px; margin-top:4px">
          WebDAV 根之后的子路径。
          <ul style="margin:4px 0; padding-left:20px">
            <li>Nextcloud: 通常是 <code>/dav/files/用户名</code></li>
            <li>坚果云 / Alist: 通常是 <code>/dav/</code></li>
            <li>不确定? 留空，先保存后用「诊断」查看实际响应</li>
          </ul>
        </div>
      </el-form-item>
      <el-form-item label="校验 TLS">
        <el-switch v-model="form.config.verify_tls" />
        <span style="margin-left:12px; color:var(--ink-500); font-size:12px">
          自签名证书时关闭
        </span>
      </el-form-item>
    </template>

    <el-form-item label="按子目录分组">
      <el-switch v-model="form.group_by_dir" />
      <span style="margin-left:12px; color:var(--ink-500); font-size:12px">
        开启后，每个子目录会生成独立的 M3U URL
      </span>
    </el-form-item>

    <el-form-item label="定时刷新 (cron)">
      <el-input v-model="form.refresh_cron" placeholder="留空 = 仅手动" />
      <div style="color:var(--ink-500); font-size:12px; margin-top:4px">
        5 字段标准 cron。例如：<code>0 */6 * * *</code> 每 6 小时，
        <code>*/30 * * * *</code> 每 30 分钟
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
