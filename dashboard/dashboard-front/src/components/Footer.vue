<script setup lang="ts">
import { envInfo } from '@/services/EnvironmentInfo'
</script>

<template>
  <q-footer elevated class="bg-grey-9 text-white">
    <div class="text-center q-my-sm">Racetrack version {{ envInfo.docker_tag }} ({{ envInfo.git_version }})</div>
  </q-footer>
</template>
