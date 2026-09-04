import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { aliases, mdi } from 'vuetify/iconsets/mdi'
import '@mdi/font/css/materialdesignicons.css'
import 'vuetify/styles'

const lightTheme = {
  dark: false,
  colors: {
    primary: '#FF9800',
    secondary: '#1a73e8',
    accent: '#FF5722',
    error: '#f44336',
    warning: '#ff9800',
    info: '#2196f3',
    success: '#4caf50',
    background: '#f5f7fa',
    surface: '#ffffff'
  }
}

const darkTheme = {
  dark: true,
  colors: {
    primary: '#FF9800',
    secondary: '#1a73e8',
    accent: '#FF5722',
    error: '#f44336',
    warning: '#ff9800',
    info: '#2196f3',
    success: '#4caf50',
    background: '#121212',
    surface: '#1e1e1e'
  }
}

export default createVuetify({
  components,
  directives,
  icons: {
    defaultSet: 'mdi',
    aliases,
    sets: { mdi }
  },
  theme: {
    defaultTheme: 'light',
    themes: {
      light: lightTheme,
      dark: darkTheme
    }
  }
})