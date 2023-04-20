export function isEmpty(str: string | null) {
    return (!str || str.length === 0 )
}

export function formatDecimalNumber(num: number | null): string {
    if (num == null)
        return ''
    return num.toFixed(2)
}
