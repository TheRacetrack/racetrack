import { createApp } from 'vue'
import App from './App.vue'

// Vuetify
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import colors from 'vuetify/lib/util/colors'

import '@mdi/font/css/materialdesignicons.css'
import './assets/main.css'

const vuetify = createVuetify({
    components,
    directives,
    theme: {
        themes: {
            light: {
                dark: false,
                colors: {
                    primary: colors.blue.darken1,
                    secondary: colors.blue.lighten4,
                }
            },
        },
    },
})

createApp(App).use(vuetify).mount('#app')
