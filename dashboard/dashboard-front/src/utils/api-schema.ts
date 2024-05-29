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
