export function isEmpty(str: string | null): boolean {
    return (!str || str.length === 0 )
}

export function isNotEmpty(str: string | null): boolean {
    return !(!str || str.length === 0 )
}

export function formatDecimalNumber(num: number | null): string {
    if (num == null)
        return ''
    return num.toFixed(2)
}

export function removeNulls(obj: any): any {
    if (Array.isArray(obj)) {
        return obj.filter(x => x != null).map(x => removeNulls(x))
    } else if (typeof obj === 'object') {
        return Object.entries(obj)
            .filter(([k, v]) => k !== null && v !== null)
            .map(([k, v]) => [k, removeNulls(v)])
            .reduce((acc: any, [k, v]) => {
                acc[k] = v
                return acc
            }, {})
    }
    return obj
}
