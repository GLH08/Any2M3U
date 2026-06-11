<script setup lang="ts">
import { onMounted, ref, onUnmounted } from 'vue'
import { api } from '@/api'
import { Monitor, FolderOpened, Clock } from '@element-plus/icons-vue'

const status = ref<any>(null)
const recent = ref<any[]>([])
let timer: any = null

async function load() {
  try {
    const r = await api.get('/api/scan/status')
    status.value = r.data
    const sr = await api.get('/api/sources')
    recent.value = (sr.data as any[]).slice(0, 5)
  } catch {}
}
onMounted(() => { load(); timer = setInterval(load, 5000) })
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <div>
    <h1 class="page-title">
      仪表盘
      <small>实时系统状态</small>
    </h1>

    <el-row :gutter="16" v-if="status">
      <el-col :span="8">
        <div class="stat-card">
          <div class="ic"><el-icon><FolderOpened /></el-icon></div>
          <div>
            <div class="v">{{ status.sources_total }}</div>
            <div class="l">已配置媒体源</div>
          </div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="stat-card">
          <div class="ic" style="background:linear-gradient(135deg,#10b981,#047857); box-shadow:0 4px 12px rgba(16,185,129,.35)">
            <el-icon><Monitor /></el-icon>
          </div>
          <div>
            <div class="v">{{ status.sources_scanning }}</div>
            <div class="l">正在扫描</div>
          </div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="stat-card">
          <div class="ic" style="background:linear-gradient(135deg,#f59e0b,#b45309); box-shadow:0 4px 12px rgba(245,158,11,.35)">
            <el-icon><Clock /></el-icon>
          </div>
          <div>
            <div class="v" style="font-size:14px; font-weight:500">{{ status.last_full_pass_at?.slice(0,19).replace('T',' ') || '—' }}</div>
            <div class="l">最近一次扫描</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <h2 class="page-title" style="margin-top:32px">最近媒体源</h2>
    <div v-if="recent.length === 0" class="empty">
      <el-icon><FolderOpened /></el-icon>
      <h3>还没有媒体源</h3>
      <p>前往「媒体源」添加你的第一个 WebDAV 或本地目录</p>
      <el-button type="primary" @click="$router.push('/sources')">添加媒体源</el-button>
    </div>
    <el-table v-else :data="recent" border>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="type" label="类型" width="100">
        <template #default="{ row }">
          <el-tag :type="row.type === 'webdav' ? 'warning' : 'success'" size="small">
            {{ row.type === 'webdav' ? 'WebDAV' : '本地' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="180">
        <template #default="{ row }">
          <el-tag v-if="row.last_scan_status === 'success'" type="success" size="small">扫描成功</el-tag>
          <el-tag v-else-if="row.last_scan_status === 'failed'" type="danger" size="small">扫描失败</el-tag>
          <el-tag v-else-if="row.last_scan_status === 'running'" type="warning" size="small">扫描中</el-tag>
          <el-tag v-else size="small">未扫描</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="last_error" label="最近错误">
        <template #default="{ row }">
          <span v-if="row.last_error" style="color:var(--danger); font-size:12px">{{ row.last_error.slice(0, 80) }}</span>
          <span v-else style="color:var(--ink-400)">—</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>
