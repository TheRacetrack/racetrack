<script setup lang="ts">
import {useRoute} from "vue-router"

const route = useRoute()
const tableName: string = route.params.table as string
const recordId: string = route.params.recordId as string
</script>

<template>

</template>