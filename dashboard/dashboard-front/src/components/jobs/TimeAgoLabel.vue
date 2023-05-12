<script setup lang="ts">
import { type Ref, ref, onMounted } from 'vue'
import { timestampPrettyAgo, timestampSecondsAgo } from '@/utils/time'

const props = defineProps({
    timestamp: { type: Number, required: false },
})
const timestamp = props.timestamp

const agoLabel: Ref<string> = ref('')

function renderAgoLabel() {
    agoLabel.value = timestampPrettyAgo(timestamp)

    const secondsAgo = timestampSecondsAgo(timestamp)
    if (secondsAgo != null) {
        if (secondsAgo <= 60) {
            setTimeout(renderAgoLabel, 1000)
        } else if (secondsAgo / 60 <= 60) {
            setTimeout(renderAgoLabel, 1000 * 60)
        } else if (secondsAgo / 60 / 60 <= 24) {
            setTimeout(renderAgoLabel, 1000 * 60 * 60)
        }
    }
}

onMounted(() => {
    renderAgoLabel()
})
</script>

<template>
    <q-badge color="primary" rounded outline>{{agoLabel}}</q-badge>
</template>
