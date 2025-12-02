// Vuetify styles
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

// RefMap brand theme for a fresh 2025 look
const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'refmap',
    themes: {
      refmap: {
        dark: false,
        colors: {
          primary: '#145DA0', // RefMap blue
          secondary: '#21CE99', // RefMap accent green
          surface: '#FFFFFF',
          background: '#F4F9FF',
          info: '#2196F3',
          success: '#21CE99',
          warning: '#FFC107',
          error: '#E53935',
        },
      },
    },
  },
  defaults: {
    VBtn: {
      rounded: 'xl',
      height: 44,
      class: 'elevate-on-hover',
    },
    VCard: {
      elevation: 6,
      rounded: 'xl',
    },
  },
})

export default vuetify
