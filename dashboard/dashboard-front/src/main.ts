import { createApp } from 'vue'

import { Quasar } from 'quasar'
import '@quasar/extras/material-icons/material-icons.css'
import 'quasar/src/css/index.sass'

import App from './App.vue'
import router from './router'

import Toast from "vue-toastification"
import "vue-toastification/dist/index.css"

import './assets/main.css'


const app = createApp(App)

app.use(router)
app.use(Quasar, {
    config: {},
    plugins: {},
})
app.use(Toast, {})

app.mount('#app')
