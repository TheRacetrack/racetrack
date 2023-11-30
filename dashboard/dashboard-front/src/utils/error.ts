import { AxiosError } from "axios"

export function extractErrorDetails(err: any): string {
    if (err instanceof AxiosError) {
        const data = err.response?.data
        if (data?.error)
            return data.error
        if (data?.type)
            return data.type
        if (err.message) {
            const method = err.config?.method?.toUpperCase();
            const message = `${err.message}: ${method} ${err.config?.url}`;
            if (data) {
                const dataJson = JSON.stringify(data);
                return `${message}: ${dataJson}`;
            };
            return message;
        }
    }
    if (err.hasOwnProperty('xhr')){
        const xhr = err.xhr
        if ('response' in xhr){
            const response = xhr['response']
            const json = JSON.parse(response)
            if (json?.error) {
                return json.error
            }
            if (json?.type) {
                return json.type
            }
        }
    }
    if (typeof err.toString === 'function') {
        return err.toString()
    }
    return JSON.stringify(err)
}
