import axios, { type AxiosResponse, type AxiosRequestConfig } from "axios"
import { authToken } from "./UserDataStore"

export const authHeader: string = 'X-Racetrack-Auth'
const basePath: string = '/dashboard'

export class ApiClient {

    get<R = AxiosResponse<any>>(
        relativeUrl: string, authorized: boolean = true,
    ): Promise<R> {
        return makeRequest('get', relativeUrl, undefined, authorized)
    }

    post<R = AxiosResponse<any>>(
        relativeUrl: string, data?: any, authorized: boolean = true,
    ): Promise<R> {
        return makeRequest('post', relativeUrl, data, authorized)
    }

    put<R = AxiosResponse<any>>(
        relativeUrl: string, data?: any, authorized: boolean = true,
    ): Promise<R> {
        return makeRequest('put', relativeUrl, data, authorized)
    }

    delete<R = AxiosResponse<any>>(
        relativeUrl: string, data?: any, authorized: boolean = true,
    ): Promise<R> {
        return makeRequest('delete', relativeUrl, data, authorized)
    }
}

function makeRequest<R = AxiosResponse<any>>(
    method: string, relativeUrl: string, data?: any, authorized: boolean = true,
): Promise<R> {
    /** Make a call to API server with an optional authorization header */
    const config: AxiosRequestConfig<any> = {
        method: method,
        url: basePath + relativeUrl,
        data: data,
    }
    if (authorized) {
        config.headers = {
            [authHeader]: authToken.value,
        }
    }
    return axios.request(config)
}

export const apiClient: ApiClient = new ApiClient()
