import { reactive, computed, type Ref } from 'vue'
import { toastService } from '@/services/ToastService'
import { apiClient } from '@/services/ApiClient'
import { isNotEmpty } from '@/utils/string'

export const envInfo: EnvironmentInfo = reactive({
    live: null,
    ready: null,
    git_version: null,
    docker_tag: null,
    lifecycle_url: null,
    external_pub_url: null,
    site_name: null,
})

export interface EnvironmentInfo {
    live: boolean | null
    ready: boolean | null
    git_version: string | null
    docker_tag: string | null
    lifecycle_url: string | null
    external_pub_url: string | null
    site_name: string | null
}

export function loadEnvironmentInfo() {
    /** Fetch backend version from API */
    apiClient.get(`/api/status`, false)
        .then(response => {
            const data: EnvironmentInfo = response.data

            envInfo.live = data.live
            envInfo.ready = data.ready
            envInfo.git_version = data.git_version
            envInfo.docker_tag = data.docker_tag
            envInfo.lifecycle_url = data.lifecycle_url
            envInfo.external_pub_url = data.external_pub_url
            envInfo.site_name = data.site_name

            if (isNotEmpty(envInfo.site_name)) {
                document.title = `[${envInfo.site_name}] Racetrack Dashboard`
            }

        }).catch(err => {
            toastService.showErrorDetails(`Backend connection failed`, err)
        })
}

export const versionFull: Ref<string> = computed(() => `${envInfo.docker_tag} (${envInfo.git_version})`)
