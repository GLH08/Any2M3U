import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as ElIcons from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import App from './App.vue'
import { router } from './router'
import './styles.css'

const app = createApp(App)

// Register all Element Plus icons globally so templates can use <el-icon><Setting/></el-icon>
for (const [name, comp] of Object.entries(ElIcons)) {
  app.component(name, comp as any)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })
app.mount('#app')
