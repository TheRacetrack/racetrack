<script setup lang="ts">
import { reactive } from 'vue'
import TheWelcome from './components/TheWelcome.vue'

const data = reactive({
  drawer: true,
      group: null,
      items: [
        {
          title: 'Foo',
          value: 'foo',
        },
        {
          title: 'Bar',
          value: 'bar',
        },
        {
          title: 'Fizz',
          value: 'fizz',
        },
        {
          title: 'Buzz',
          value: 'buzz',
        },
      ],
})
</script>

<template>
  <v-app>
    <v-layout>

      <v-app-bar
        color="surface-variant"
        prominent
      >
        <v-app-bar-nav-icon variant="text" @click.stop="data.drawer = !data.drawer"></v-app-bar-nav-icon>

        <v-toolbar-title>Racetrack Dashboard</v-toolbar-title>

        <v-spacer></v-spacer>

        <v-btn variant="text" icon="mdi-magnify"></v-btn>

        <v-btn variant="text" icon="mdi-filter"></v-btn>

        <v-btn variant="text" icon="mdi-dots-vertical"></v-btn>
      </v-app-bar>

      <v-navigation-drawer
        v-model="data.drawer"
        location="left"
        density="compact"
        permanent
        absolute
      >
        <v-list
          nav
        >
          <v-list-item prepend-icon="mdi-view-dashboard" title="Home" value="home" active-color="primary"></v-list-item>
          <v-list-item prepend-icon="mdi-forum" title="About" value="about"></v-list-item>
      </v-list>
      </v-navigation-drawer>

      <v-main style="min-height: 300px;">
        <v-container fill-height>
          Main
        </v-container>
      </v-main>

      <v-footer app>Footer</v-footer>
    </v-layout>
  </v-app>
</template>
