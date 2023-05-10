import type { JobData } from "./api-schema"
import { envInfo } from '@/services/EnvironmentInfo'

export enum JobOrder {
    ByLatestFamily,
    ByLatestJob,
    ByName,
    ByStatus,
}

export function sortedJobs(jobs: JobData[], order: JobOrder) {
    const sortedJobs: JobData[] = [...jobs]
    if (order === JobOrder.ByLatestFamily || order === JobOrder.ByLatestJob) {
        sortedJobs.sort((a, b) => {
            return b.update_time - a.update_time
        })
    } else if (order === JobOrder.ByName) {
        sortedJobs.sort((a, b) => {
            return compareJobNames(a, b)
                || compareVersions(b.version, a.version)
        })
    } else if (order === JobOrder.ByStatus) {
        sortedJobs.sort((a, b) => {
            return statusImportance(a.status) - statusImportance(b.status)
                || compareJobNames(a, b)
                || compareVersions(b.version, a.version)
        })
    }
    return sortedJobs
}

function compareVersions(a: string, b: string): number {
    const regexp = /^(\d+)\.(\d+)\.(\d+)(.*)$/g
    const matchesA = regexp.exec(a)
    regexp.lastIndex = 0
    const matchesB = regexp.exec(b)
    if (!matchesA || !matchesB) {
        return 0
    }
    return parseInt(matchesA[1]) - parseInt(matchesB[1])
        || parseInt(matchesA[2]) - parseInt(matchesB[2])
        || parseInt(matchesA[3]) - parseInt(matchesB[3])
        || matchesA[4].localeCompare(matchesB[4])
}

function compareJobNames(a: JobData, b: JobData): number {
    return a.name.toLowerCase().localeCompare(b.name.toLowerCase())
}

function statusImportance(status: string): number {
    switch (status) {
        case "running":
            return 0
        case "error":
            return -2
        default:
            return -1
    }
}

export function filterJobByKeyword(job: JobData, keyword: string): boolean {
    if (job.name.toLowerCase().includes(keyword))
        return true
    if (job.version.toLowerCase().includes(keyword))
        return true
    if (job.deployed_by?.toLowerCase().includes(keyword))
        return true
    if (job.status.toLowerCase().includes(keyword))
        return true
    if (job.job_type_version?.toLowerCase().includes(keyword))
        return true
    if (job.manifest?.['owner_email']?.toLowerCase().includes(keyword))
        return true
    return false
}

export function getJobGraphanaUrl(job: JobData): string {
    // "Jobs" dashboard filtered by job name and version
    return `${envInfo.grafana_url}/d/KZoFMs_nz/jobs?orgId=1&var-job_name=${job.name}&var-job_version=${job.version}`
}
