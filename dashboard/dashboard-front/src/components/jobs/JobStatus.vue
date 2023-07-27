<script setup lang="ts">
import { type Ref, computed } from 'vue'

const props = defineProps({
    status: { type: String, required: false },
    short: { type: Boolean, required: false, default: false },
})
const status: Ref<string> = computed(() => props.status || "")
const color: Ref<string> = computed(() => {
    switch (status.value) {
        case "running": 
            return "green"
        case "error": 
            return "red"
        default: 
            return "orange"
    }
})
</script>

<template>
    <template v-if="short">
        <q-badge rounded :color="color">
            <q-tooltip>{{status.toUpperCase()}}</q-tooltip>
        </q-badge>
    </template>
    <template v-else>
        <q-badge :color="color" text-color="white" :label="status.toUpperCase()" />
    </template>
</template>
