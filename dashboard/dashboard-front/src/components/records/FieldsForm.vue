<script setup lang="ts">
import {computed, type Ref} from "vue"
import {type FormFields} from "@/components/records/records"

const props = defineProps<{
    formFields: FormFields
}>()
const fieldTypes: Ref<Record<string, string>> = computed(() => {
    return props.formFields.types
})
const fieldNames: Ref<string[]> = computed(() => {
    return props.formFields.names
})
const fieldValues: Ref<Record<string, any>> = computed(() => {
    return props.formFields.values
})
</script>

<template>
    <div v-for="fieldName in fieldNames" :key="fieldName">
        <template v-if="['str', 'str | None'].includes(fieldTypes[fieldName])">
            <q-input
                outlined autogrow
                v-model="fieldValues[fieldName]"
                :label="fieldName"
                type="text"
                >
                <template v-slot:append>
                    <q-icon v-if="fieldTypes[fieldName].endsWith(' | None')"
                            name="cancel" @click.stop.prevent="fieldValues[fieldName] = null" class="cursor-pointer" />
                </template>
            </q-input>
        </template>
        <template v-else-if="['int', 'int | None', 'float', 'float | None'].includes(fieldTypes[fieldName])">
            <q-input
                outlined
                v-model="fieldValues[fieldName]"
                :label="fieldName"
                type="number"
                >
                <template v-slot:append>
                    <q-icon v-if="fieldTypes[fieldName].endsWith(' | None')"
                            name="cancel" @click.stop.prevent="fieldValues[fieldName] = null" class="cursor-pointer" />
                </template>
            </q-input>
        </template>
        <template v-else-if="['datetime', 'datetime | None'].includes(fieldTypes[fieldName])">
            <q-input outlined :label="fieldName" v-model="fieldValues[fieldName]">
              <template v-slot:append>
                    <q-icon v-if="fieldTypes[fieldName].endsWith(' | None')"
                            name="cancel" @click.stop.prevent="fieldValues[fieldName] = null" class="cursor-pointer" />
                <q-icon name="event" class="cursor-pointer">
                  <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                    <div class="row items-center justify-end">
                      <q-date v-model="fieldValues[fieldName]" mask="YYYY-MM-DD, HH:mm:ss.SSS Z" first-day-of-week="1" today-btn />
                      <q-time v-model="fieldValues[fieldName]" mask="YYYY-MM-DD, HH:mm:ss.SSS Z" color="primary" format24h with-seconds now-btn />
                    </div>
                    <div class="row items-center justify-end">
                      <q-btn v-close-popup label="Close" color="primary" flat />
                    </div>
                  </q-popup-proxy>
                </q-icon>
              </template>
            </q-input>
        </template>
        <template v-else-if="fieldTypes[fieldName] == 'bool'">
            <q-checkbox v-model="fieldValues[fieldName]" :label="fieldName" />
        </template>
        <template v-else>
            <q-input
                outlined readonly
                :label="fieldName"
                type="text"
                model-value="[Unreadable data]" />
        </template>
    </div>
</template>
