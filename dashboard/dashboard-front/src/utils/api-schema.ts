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
    image_tag?: string
    deployed_by?: string
    last_call_time?: number
    infrastructure_target?: string
    replica_internal_names: string[]
    job_type_version: string
}

export interface DocPageContent {
    doc_name: string
    html_content: string
}
