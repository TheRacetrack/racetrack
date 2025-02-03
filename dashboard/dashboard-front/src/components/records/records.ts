import type {TableMetadataPayload} from "@/utils/api-schema"
import {apiClient} from "@/services/ApiClient"
import {toastService} from "@/services/ToastService"
import {type Ref} from "vue"
import {formatDateUtcIso8601, leftZeroPad} from "@/utils/time"

export const emptyTableMetadata: TableMetadataPayload = {
    class_name: '',
    table_name: '',
    plural_name: '',
    primary_key_column: '',
    main_columns: [],
    all_columns: [],
    column_types: {},
}

const allowedTypes = ['str', 'str | None', 'int', 'int | None', 'float', 'float | None', 'datetime', 'datetime | None', 'bool']

export interface FormFields {
    names: string[]
    values: Record<string, any>
    types: Record<string, any>
}

export async function fetchTableMetadata(loading: Ref<boolean>, tableMetadata: Ref<TableMetadataPayload>, tableName: string): Promise<void> {
    loading.value = true
    try {
        let response = await apiClient.get<TableMetadataPayload>(`/api/v1/records/table/${tableName}/metadata`)
        tableMetadata.value = response.data
    } catch (err) {
        toastService.showErrorDetails(`Failed to fetch table data`, err)
    } finally {
        loading.value = false
    }
}

export function decodeInputValue(value: any, fieldName: string, tableMetadata: TableMetadataPayload): any {
    const colType = tableMetadata.column_types[fieldName]
    if (colType.endsWith(' | None') && (value == null || value === '')) {
        return value
    }
    if (['datetime', 'datetime | None'].includes(colType)) {
        const date = new Date(value)
        const day = leftZeroPad(date.getDate(), 2)
        const month = leftZeroPad(date.getMonth() + 1, 2)
        const year = leftZeroPad(date.getFullYear(), 4)
        const hour = leftZeroPad(date.getHours(), 2)
        const minute = leftZeroPad(date.getMinutes(), 2)
        const second = leftZeroPad(date.getSeconds(), 2)
        const millisecond = leftZeroPad(date.getMilliseconds(), 3)
        const timezoneOffset = -date.getTimezoneOffset() ?? 0
        const timezoneHours = leftZeroPad(Math.floor(Math.abs(timezoneOffset) / 60), 2)
        const timezoneMinutes = leftZeroPad(Math.abs(timezoneOffset) % 60, 2)
        const timezonePart = timezoneOffset >= 0 ? `+${timezoneHours}:${timezoneMinutes}` : `-${timezoneHours}:${timezoneMinutes}`
        return `${year}-${month}-${day}, ${hour}:${minute}:${second}.${millisecond} ${timezonePart}`
    }
    return value
}

export function encodeInputValue(value: any, colType: string): any {
    if (colType.endsWith(' | None') && (value == null || value === '')) {
        return null
    }
    if (colType === 'str' && value == null) {
        return ''
    }
    if (['datetime', 'datetime | None'].includes(colType)) {
        return formatDateUtcIso8601(value)
    }
    return value
}

export function encodeInputValues(formFields: FormFields): Record<string, any> {
    return Object.fromEntries(
        Object.entries(formFields.values)
            .filter(([key, _]) => allowedTypes.includes(formFields.types[key]))
            .map(([key, value]) => [key, encodeInputValue(value, formFields.types[key])])
    ) as Record<string, any>
}

export function decodeInputValues(fields: Record<string, any>, tableMetadata: TableMetadataPayload): Record<string, any>  {
    return Object.fromEntries(
            Object.entries(fields)
                .map(([key, value]) => [key, decodeInputValue(value, key, tableMetadata)])
        ) as Record<string, any>
}