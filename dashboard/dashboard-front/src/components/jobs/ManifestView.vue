<script setup lang="ts">
import { type Ref, computed } from 'vue'
import hljs from 'highlight.js/lib/core'
import hljs_yaml from 'highlight.js/lib/languages/yaml'
import 'highlight.js/styles/github.css'

hljs.registerLanguage('yaml', hljs_yaml)

const props = defineProps({
    manifestYaml: { type: String, required: false },
})

const manifestHtml: Ref<string> = computed(() => {
    const manifestYamlN = props.manifestYaml ?? ''
    return hljs.highlight(manifestYamlN, {language: 'yaml'}).value
})
</script>

<template>
    <div class="x-monospace x-overflow-any" v-html="manifestHtml" style="white-space: pre;"></div>
</template>
