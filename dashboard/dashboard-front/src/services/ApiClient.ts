import axios, { type AxiosResponse, type AxiosRequestConfig } from "axios"
import { authToken } from "./UserDataStore"

export const authHeader: string = 'X-Racetrack-Auth'
const basePath: string = '/dashboard'

export class ApiClient {

    get<R>(
        relativeUrl: string, authorized: boolean = true,
    ): Promise<AxiosResponse<R>> {
        return makeRequest<AxiosResponse<R>>('get', relativeUrl, undefined, authorized)
    }

    post<R>(
        relativeUrl: string, data?: any, authorized: boolean = true,
    ): Promise<AxiosResponse<R>> {
        return makeRequest<AxiosResponse<R>>('post', relativeUrl, data, authorized)
    }

    put<R>(
        relativeUrl: string, data?: any, authorized: boolean = true,
    ): Promise<AxiosResponse<R>> {
        return makeRequest<AxiosResponse<R>>('put', relativeUrl, data, authorized)
    }

    delete<R>(
        relativeUrl: string, data?: any, authorized: boolean = true,
    ): Promise<AxiosResponse<R>> {
        return makeRequest<AxiosResponse<R>>('delete', relativeUrl, data, authorized)
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
