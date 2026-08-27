import { createApp } from 'vue'
import VXETable from 'vxe-table'
import 'vxe-table/lib/style.css'
import 'remixicon/fonts/remixicon.css'
import App from './App.vue'
import './style.css'

createApp(App).use(VXETable).mount('#app')
