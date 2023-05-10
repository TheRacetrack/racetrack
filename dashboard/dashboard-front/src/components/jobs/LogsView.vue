<script setup lang="ts">
import { computed, type Ref } from 'vue'

const props = defineProps({
    title: { type: String, required: true },
    content: { type: String, required: true },
    open: { type: Boolean, required: true },
})

const title: Ref<string> = computed(() => props.title)
const content: Ref<string> = computed(() => props.content)
const open: Ref<boolean> = computed(() => props.open)

const emit = defineEmits(['close'])

function close() {
    emit('close', null)
}
</script>

<template>
    <q-dialog
      v-model="open"
      persistent
      maximized
      transition-show="slide-up"
      transition-hide="slide-down"
      @update:model-value="(value) => {}"
    >
      <q-card class="">
        <q-bar>
          <q-space />
          <q-btn dense flat icon="close" v-close-popup @click="close()">
            <q-tooltip>Close</q-tooltip>
          </q-btn>
        </q-bar>

        <q-card-section>
          <div class="text-h6">{{title}}</div>
        </q-card-section>
        <q-card-section class="q-pt-none">
            <pre class="x-monospace">{{content}}</pre>
        </q-card-section>
      </q-card>
    </q-dialog>
</template>
