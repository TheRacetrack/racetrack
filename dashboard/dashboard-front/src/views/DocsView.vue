<script setup lang="ts">
import { ref, type Ref, onMounted } from 'vue'
import { toastService } from '@/services/ToastService'
import { apiClient } from '@/services/ApiClient'
import { timestampToLocalTime } from '@/services/DateUtils'

const docIndexData: Ref<DocIndexData> = ref({
    doc_pages: [],
    plugin_pages: [],
} as DocIndexData)

interface DocIndexData {
    doc_pages: PageData[]
    plugin_pages: PageData[]
}

interface PageData {
    title: string
    url: string
}

interface PageContent {
    doc_name: string
    html_content: string
}

function fetchAuditLogData() {
    apiClient.get(`/api/docs/index`).then(response => {
        docIndexData.value = response.data
    }).catch(err => {
        toastService.showErrorDetails(`Failed to fetch documentation`, err)
    })
}

onMounted(() => {
    fetchAuditLogData()
})
</script>

<template>
    <q-card>
        <q-card-section class="q-pb-none">
            <div class="text-h6">Documentation Index</div>
        </q-card-section>
        <q-card-section>

            <q-list bordered separator class="rounded-borders">
                <q-item-label header>Static Documentation Pages</q-item-label>

                <q-item clickable v-ripple v-for="page in docIndexData.doc_pages"
                    :to="{name: 'jobs'}">
                    <q-item-section>
                        <q-item-label>{{ page.title }}</q-item-label>
                    </q-item-section>
                </q-item>
            </q-list>

        </q-card-section>
        <q-card-section>

            <q-list bordered separator class="rounded-borders">
                <q-item-label header>Plugin Pages</q-item-label>

                <q-item clickable v-ripple v-for="page in docIndexData.plugin_pages">
                    <q-item-section>
                        <q-item-label>{{ page.title }}</q-item-label>
                    </q-item-section>
                </q-item>
            </q-list>

            <article class="markdown-body" style="padding-top: 0;">
            </article>

        </q-card-section>
    </q-card>
</template>

<style scoped>
.markdown-body {
    box-sizing: border-box;
    min-width: 200px;
    max-width: 980px;
    margin: 0 auto;
    padding: 45px;
}

@media (max-width: 767px) {
    .markdown-body {
        padding: 15px;
    }
}
</style>