<script setup lang="ts">
import type { QAjaxBar } from 'quasar';
import { ref, defineExpose, type Ref } from 'vue'

const dialogOpen = ref(false)
const dialogBody = ref('')
const confirmationCallback = ref(() => {})
const loadingBar: Ref<QAjaxBar | null> = ref(null)

function showDialog(body: string, callback: () => void) {
  dialogBody.value = body
  confirmationCallback.value = callback
  dialogOpen.value = true
}

function clickConfirm() {
  confirmationCallback.value()
}

function startLoading() {
  loadingBar.value?.start()
}

function stopLoading() {
  loadingBar.value?.stop()
}

defineExpose({
  showDialog,
  startLoading,
  stopLoading,
})
</script>

<template>
  <q-dialog v-model="dialogOpen">
    <q-card>
      <q-card-section>
        <div class="text-h6">Are you sure?</div>
      </q-card-section>
      
      <q-card-section class="q-pt-none">{{ dialogBody }}</q-card-section>
      
      <q-card-actions align="right">
        <q-btn flat color="white" text-color="black" label="Cancel" v-close-popup />
        <q-btn flat color="primary" label="Confirm" v-close-popup @click="clickConfirm" />
      </q-card-actions>
    </q-card>
  </q-dialog>
  <q-ajax-bar
    ref="loadingBar"
    position="top"
    color="primary"
    size="4px"
    skip-hijack
    />
</template>
