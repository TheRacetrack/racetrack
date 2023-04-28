<script setup lang="ts">
import { type Ref, computed } from 'vue'

const props = defineProps(['status'])
const status: Ref<string | null> = computed(() => props.status)
</script>

<template>
    <q-badge v-if="status == 'running'" color="green" text-color="white" label="RUNNING" />
    <q-badge v-else-if="status == 'error'" color="red" text-color="white" label="ERROR" />
    <q-badge v-else color="orange" text-color="white" :label="status" />
</template>
