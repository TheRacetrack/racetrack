export function formatTimestampIso8601(timestampS: number | undefined): string {
    if (timestampS == null) {
        return ''
    }
    const date = new Date(timestampS * 1000)
    return date.toISOString()
}
