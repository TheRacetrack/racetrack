<script setup lang="ts">
import { ref, type Ref, onMounted } from 'vue'
import { toastService } from '@/services/ToastService'
import { apiClient } from '@/services/ApiClient'
import 'github-markdown-css/github-markdown.css'

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

function fetchDocIndexData() {
    apiClient.get<DocIndexData>(`/api/docs/index`).then(response => {
        docIndexData.value = response.data
    }).catch(err => {
        toastService.showErrorDetails(`Failed to fetch documentation`, err)
    })
}

onMounted(() => {
    fetchDocIndexData()
})
</script>

<template>
    <q-card>
        <q-card-section>
            <div class="markdown-body" style="padding-top: 0;">

                <h1>Racetrack Documentation</h1>
                <h2>Choose your character</h2>
                <p>If you are:</p>
                <ul>
                    <li>
                        <p>Racetrack User, see:</p>
                        <ul>
                        <li><router-link :to="{name: 'docs-page', params: {pageName: 'user.md'}}">User Guidelines</router-link> - what is Racetrack, getting started, tutorial</li>
                        <li><router-link :to="{name: 'docs-page', params: {pageName: 'manifest-schema.md'}}">Job Manifest File Schema</router-link> - list of available YAML fields</li>
                        <li><router-link :to="{name: 'docs-page', params: {pageName: 'development/using-plugins.md'}}">Using plugins</router-link> - 
                        how to install plugins</li>
                        <li><router-link :to="{name: 'docs-page', params: {pageName: 'glossary.md'}}">Glossary</router-link> - terminology explained</li>
                        <li><router-link :to="{name: 'docs-page', params: {pageName: 'CHANGELOG.md'}}">CHANGELOG</router-link> - latest user-facing, notable changes</li>
                        </ul>
                    </li>
                    <li>
                        <p>Racetrack Admin, see:</p>
                        <ul>
                        <li><router-link :to="{name: 'docs-page', params: {pageName: 'admin.md'}}">Admin guidelines</router-link> - 
                        guidelines for portfolio managers and administrators.</li>
                        </ul>
                    </li>
                    <li>
                        <p>Racetrack Developer, see:</p>
                        <ul>
                        <li><router-link :to="{name: 'docs-page', params: {pageName: 'development/develop.md'}}">Developer manual</router-link> - 
                        development setup, deployment, testing, releasing version</li>
                        <li><router-link :to="{name: 'docs-page', params: {pageName: 'development/developing-plugins.md'}}">Developing plugins</router-link> - 
                        how to create plugins</li>
                        </ul>
                    </li>
                </ul>
                
                <h2>All Pages Index</h2>

                <ul>
                    <li>Static Pages
                        <ul>
                            <li v-for="page in docIndexData.doc_pages">
                                <router-link :to="{name: 'docs-page', params: {pageName: page.url}}">{{ page.title }}</router-link>
                            </li>
                        </ul>
                    </li>
                    <li>Plugin Pages
                        <ul>
                            <li v-for="page in docIndexData.plugin_pages">
                                <router-link :to="{name: 'docs-plugin', params: {pageName: page.url}}">{{ page.title }}</router-link>
                            </li>
                        </ul>
                    </li>
                    <li>
                        <a href="https://theracetrack.github.io/racetrack/" target="_blank">Racetrack Manual</a>
                    </li>
                </ul>

            </div>
        </q-card-section>
    </q-card>
</template>
