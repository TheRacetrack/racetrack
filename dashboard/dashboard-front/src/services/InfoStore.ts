import { reactive } from 'vue'
import axios from "axios"
import { ToastService } from './ToastService'

export const backendStatus: BackendInfo = reactive({
    live: null,
    ready: null,
    git_version: null,
    docker_tag: null,
})

export interface BackendInfo {
    live: boolean | null
    ready: boolean | null
    git_version: string | null
    docker_tag: string | null
}

export function loadBackendStatus() {
    /** Fetch backend version from API */
    axios.get(`/api/status`)
        .then(response => {
            const responseData: BackendInfo = response.data

            backendStatus.live = responseData.live
            backendStatus.ready = responseData.ready
            backendStatus.git_version = responseData.git_version
            backendStatus.docker_tag = responseData.docker_tag

        }).catch(err => {
            ToastService.showRequestError(`Backend connection failed`, err)
        })
}
