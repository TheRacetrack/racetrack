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
