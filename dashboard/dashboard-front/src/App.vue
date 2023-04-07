<script setup lang="ts">
import TheWelcome from './components/TheWelcome.vue'
</script>

<template>
  <v-app>
    <v-layout>
      <v-app-bar color="surface-variant" title="Racetrack Dashboard" :elevation="2">
        <template v-slot:append>
          <v-btn icon="mdi-heart"></v-btn>

          <v-btn icon="mdi-magnify"></v-btn>

          <v-btn icon="mdi-dots-vertical"></v-btn>
        </template>
      </v-app-bar>

      <v-navigation-drawer
        fixed
        permanent
        clipped
        app
      >
        <v-list
          dense
        >
          <v-list-item prepend-icon="mdi-view-dashboard" title="Home" value="home"></v-list-item>
          <v-list-item prepend-icon="mdi-forum" title="About" value="about"></v-list-item>
        </v-list>
      </v-navigation-drawer>

      <v-main style="min-height: 300px;">
        <v-container fluid fill-height>
        Main
        </v-container>
      </v-main>

      <v-footer app>Footer</v-footer>
    </v-layout>
  </v-app>
</template>
