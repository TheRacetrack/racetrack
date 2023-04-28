<script setup lang="ts">
import GraphArea from '@/components/jobs/graph/GraphArea.vue'
</script>

<template>
  <q-card>
    <q-card-section>
      <div class="text-h6">Dependencies Graph</div>
    </q-card-section>

    <q-card-section class="q-pt-none">
      <GraphArea/>
    </q-card-section>
  </q-card>
</template>
