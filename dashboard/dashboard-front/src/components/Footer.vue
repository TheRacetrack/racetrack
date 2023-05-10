<script setup lang="ts">
import { versionFull } from '@/services/EnvironmentInfo'
</script>

<template>
  <q-footer elevated class="bg-grey-7 text-white">
    <div class="text-center q-my-sm">Racetrack version {{ versionFull }}</div>
  </q-footer>
</template>
