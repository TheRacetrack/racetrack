export interface JobData {
    name: string
    version: string
    status: string
    create_time: number
    update_time: number
    id?: string
    manifest?: Record<string, any>
    manifest_yaml?: string
    internal_name?: string
    pub_url?: string
    error?: string
    notice?: string
    image_tag?: string
    deployed_by?: string
    last_call_time?: number
    infrastructure_target?: string
    replica_internal_names: string[]
    job_type_version: string
    infrastructure_stats: Record<string, any>
}

export interface DocPageContent {
    doc_name: string
    html_content: string
}

export interface DeploymentDto {
    id: string
    status: string
    create_time: number
    update_time: number
    error?: string
    deployed_by?: string
    phase?: string
    image_name?: string
    infrastructure_target?: string
    manifest_yaml: string
    job_name: string
    job_version: string
}

export interface EscDto {
    name: string
    id?: string
}

export interface AuthTokenData {
    id: string
    token: string
    expiry_time?: number
    active: boolean
    last_use_time?: number
}

export interface EscAuthData {
    id: string
    name: string
    tokens: AuthTokenData[]
}

export interface TableMetadataPayload {
    class_name: string
    table_name: string
    plural_name: string
    primary_key_column: string
    main_columns: string[]
    all_columns: string[]
    column_types: Record<string, string>
    foreign_keys: Record<string, string>
}

export interface RecordFieldsPayload {
    fields: Record<string, any>
}

export interface FetchManyRecordsRequest {
    offset: number
    limit: number | null
    order_by: string[] | null
    filters: Record<string, any> | null
    columns: string[] | null
}

export interface FetchManyRecordsResponse {
    columns: string[]
    primary_key_column: string
    records: RecordFieldsPayload[]
}

export interface CountRecordsRequest {
    filters: Record<string, any> | null
}

export interface ManyRecordsRequest {
    record_ids: string[]
}

export interface FetchManyNamesResponse {
    id_to_name: Record<string, string>
}
