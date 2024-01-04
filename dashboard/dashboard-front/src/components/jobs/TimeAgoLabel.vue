<script setup lang="ts">
import { type Ref, ref, watch, onMounted, onUnmounted } from 'vue'
import { timestampPrettyAgo, timestampSecondsAgo } from '@/utils/time'

const props = defineProps({
    timestamp: { type: Number, required: false },
})
const agoLabel: Ref<string> = ref('')
const timerId: Ref<NodeJS.Timeout | null> = ref(null)

watch(() => props.timestamp, () => {
    renderAgoLabel()
})

function renderAgoLabel() {
    agoLabel.value = timestampPrettyAgo(props.timestamp)

    const secondsAgo = timestampSecondsAgo(props.timestamp)
    if (timerId.value != null) {
        clearTimeout(timerId.value)
    }
    if (secondsAgo != null) {
        if (secondsAgo <= 60) {
            timerId.value = setTimeout(renderAgoLabel, 1000)
        } else if (secondsAgo / 60 <= 60) {
            timerId.value = setTimeout(renderAgoLabel, 1000 * 60)
        } else if (secondsAgo / 60 / 60 <= 24) {
            timerId.value = setTimeout(renderAgoLabel, 1000 * 60 * 60)
        } else {
            timerId.value = null
        }
    }
}

onMounted(() => {
    renderAgoLabel()
})

onUnmounted(() => {
    if (timerId.value != null) {
        clearTimeout(timerId.value)
    }
})
</script>

<template>
    <q-badge color="primary" rounded outline>{{agoLabel}}</q-badge>
</template>
