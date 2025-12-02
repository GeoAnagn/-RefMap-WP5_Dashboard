import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import vuetify from './plugins/vuetify'
import '@mdi/font/css/materialdesignicons.css'
import 'leaflet/dist/leaflet.css';

createApp(App)
  .use(vuetify)
  .mount('#app')
