<script setup lang="ts">
import { backendStatus } from '@/services/InfoStore'
</script>

<template>
  <q-footer elevated class="bg-grey-9 text-white">
    <div class="text-center q-my-sm">Racetrack version {{ backendStatus.docker_tag }} ({{ backendStatus.git_version }})</div>
  </q-footer>
</template>
