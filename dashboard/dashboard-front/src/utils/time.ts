export function formatTimestampIso8601(timestampS: number | undefined): string {
    if (!timestampS) {
        return ''
    }
    const date = new Date(timestampS * 1000)
    return date.toISOString()
}

export function formatDateIso8601(timestampS: number | undefined): string {
    if (!timestampS) {
        return ''
    }
    const date = new Date(timestampS * 1000)
    const day = leftZeroPad(date.getDate(), 2)
    const month = leftZeroPad(date.getMonth() + 1, 2)
    const year = leftZeroPad(date.getFullYear(), 4)
    return `${year}-${month}-${day}`
}

export function timestampToLocalTime(timestampS: number | undefined): string {
    if (!timestampS) {
        return ''
    }
    const date = new Date(timestampS * 1000)
    return date.toString()
}

export function timestampPrettyAgo(timestampS: number | undefined): string {
    /**
    Convert past date to user-friendly description compared to current datetime.
    eg.: 'an hour ago', 'yesterday', '3 months ago', 'just now'
    */
    if (!timestampS)
        return 'never'

    const diffMs = new Date().getTime() - timestampS * 1000
    const diffSeconds = Math.floor(diffMs / 1000)
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffDays < 0)
        return ''
    if (diffDays === 0) {
        if (diffSeconds < 10)
            return 'just now'
        if (diffSeconds < 60)
            return `${diffSeconds} seconds ago`
        if (diffSeconds < 120)
            return 'a minute ago'
        if (diffSeconds < 3600)
            return `${Math.floor(diffSeconds / 60)} minutes ago`
        if (diffSeconds < 7200)
            return 'an hour ago'
        if (diffSeconds < 86400)
            return `${Math.floor(diffSeconds / 3600)} hours ago`
    }
    if (diffDays === 1)
        return 'yesterday'
    if (diffDays < 7)
        return `${diffDays} days ago`
    if (Math.floor(diffDays / 7) === 1)
        return 'a week ago'
    if (diffDays < 31)
        return `${Math.floor(diffDays / 7)} weeks ago`
    if (Math.floor(diffDays / 30) === 1)
        return 'a month ago'
    if (diffDays < 365)
        return `${Math.floor(diffDays / 30)} months ago`
    if (Math.floor(diffDays / 365) === 1)
        return 'a year ago'
    return `${Math.floor(diffDays / 365)} years ago`
}

export function timestampSecondsAgo(timestampS: number | undefined): number | null {
    if (!timestampS)
        return null
    const diffMs = new Date().getTime() - timestampS * 1000
    return Math.floor(diffMs / 1000)
}

export function formatDuration(timestampStart: number | undefined, timestampEnd: number | undefined): string {
    if (timestampStart == null || timestampEnd == null)
        return ''

    const totalSeconds = timestampEnd - timestampStart
    const seconds = totalSeconds % 60
    const minutes = Math.floor(totalSeconds / 60) % 60
    const hours = Math.floor(totalSeconds / 60 / 60) % 24
    const days = Math.floor(totalSeconds / 60 / 60 / 24)

    if (totalSeconds < 0)
        return ''
    if (days > 0)
        return `${days}d ${hours}h ${minutes}m ${seconds}s`
    if (hours > 0)
        return `${hours}h ${minutes}m ${seconds}s`
    if (minutes > 0)
        return `${minutes}m ${seconds}s`
    return `${seconds}s`
}

export function leftZeroPad(num: number, size: number): string {
    let s = num + ""
    while (s.length < size)
        s = "0" + s
    return s
}
