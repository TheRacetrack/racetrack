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
        const newObj: any = {}
        for (let [k, v] of Object.entries(obj)) {
            if (k !== null && v !== null) {
                newObj[k] = removeNulls(v)
            }
        }
        return newObj
    }
    return obj
}
