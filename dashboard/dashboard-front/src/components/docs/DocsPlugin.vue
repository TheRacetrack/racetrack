<script setup lang="ts">
import { ref, type Ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { toastService } from '@/services/ToastService'
import { apiClient } from '@/services/ApiClient'
import type { DocPageContent } from '@/utils/api-schema'

const route = useRoute()
const pageName = route.params.pageName

const docPageContent: Ref<DocPageContent> = ref({
    doc_name: '',
    html_content: '',
})

function fetchDocPageData() {
    apiClient.get<DocPageContent>(`/api/docs/plugin/${pageName}`).then(response => {
        docPageContent.value = response.data
    }).catch(err => {
        toastService.showErrorDetails(`Failed to fetch documentation page`, err)
    })
}

onMounted(() => {
    fetchDocPageData()
})
</script>

<template>
    <q-card>
        <q-card-section class="q-py-lg">
            <div class="markdown-body">
                <h1>{{ docPageContent.doc_name }}</h1>
                <div style="padding-top: 0;" v-html="docPageContent.html_content"></div>
            </div>
        </q-card-section>
    </q-card>
</template>
