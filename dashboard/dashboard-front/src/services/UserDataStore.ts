import { ref, type Ref } from 'vue'
import { type Router } from 'vue-router'
import { apiClient } from '@/services/ApiClient'
import { toastService } from '@/services/ToastService'
import { AxiosError } from 'axios'

export const isAuthenticated: Ref<boolean> = ref(false)
export const username: Ref<string> = ref('')
export const authToken: Ref<string> = ref('')
export const isAdmin: Ref<boolean> = ref(false)

const AUTH_COOKIE_NAME = 'X-Racetrack-Auth'

export interface UserData {
    username: string
    authToken: string
    isAdmin: boolean
}

export interface UserProfileDto {
    username: string
    token: string
    is_staff: boolean
}

export function setUserData(data: UserData) {
    isAuthenticated.value = true
    username.value = data.username
    authToken.value = data.authToken
    isAdmin.value = data.isAdmin
    saveUserData()
}

export function setAuthToken(newToken: string) {
    authToken.value = newToken
    saveUserData()
}

export function deleteUserData() {
    isAuthenticated.value = false
    username.value = ''
    authToken.value = ''
    isAdmin.value = false
    saveUserData()
}

export function loadUserData(router: Router) {
    /** Load stored auth token and fetch more details about user account */
    const storedAuthToken = localStorage.getItem('userData.authToken')
    if (!storedAuthToken) {
        return
    }
    
    authToken.value = storedAuthToken as string
    isAuthenticated.value = true

    apiClient.get(`/api/v1/users/validate_user_auth`, true)
        .then(response => {
            const data: UserProfileDto = response.data
            isAuthenticated.value = true
            username.value = data.username
            isAdmin.value = data.is_staff

        }).catch(err => {
            if (err instanceof AxiosError && err.response?.status == 401) {
                deleteUserData()
                router.push({ name: 'login' })
                toastService.showErrorDetails(`Invalid user data`, err)
            } else {
                isAuthenticated.value = false
                username.value = ''
                authToken.value = ''
                isAdmin.value = false
                toastService.showErrorDetails(`Failed to fetch user data`, err)
            }
        })
}

function saveUserData() {
    if (!authToken.value) {
        localStorage.removeItem('userData.authToken')
    } else {
        localStorage.setItem('userData.authToken', authToken.value)
    }
}

export function hasAuthCookie(): boolean {
    return getCookie(AUTH_COOKIE_NAME) != null
}

function getCookie(name: string): string | null {
    const nameLenPlus = name.length + 1
    const values = document.cookie
        .split(';')
        .map(c => c.trim())
        .filter(cookie => cookie.substring(0, nameLenPlus) === `${name}=`)
        .map(cookie => decodeURIComponent(cookie.substring(nameLenPlus)))
    return values[0] || null
}
