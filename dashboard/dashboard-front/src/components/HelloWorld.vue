<script setup lang="ts">
import { ref } from 'vue'

const count = ref(0)
</script>

<template>
  <h1>Jobs</h1>

  <div class="card">
    <button type="button" @click="count++">count is {{ count }}</button>
    <p>
      Edit
      <code>components/HelloWorld.vue</code> to test HMR
    </p>
  </div>

</template>
