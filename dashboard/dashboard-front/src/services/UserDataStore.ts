import { reactive } from 'vue'
import { isEmpty } from './StringUtils';

export const userData: UserData = reactive({
    isAuthenticated: false,
    username: 'dupa',
    authToken: '',
    isAdmin: false,
})

export interface UserData {
    isAuthenticated: boolean;
    username: string | null;
    authToken: string | null;
    isAdmin: boolean;
}

export function setUserData(data: UserData) {
    userData.isAuthenticated = data.isAuthenticated
    userData.username = data.username
    userData.authToken = data.authToken
    userData.isAdmin = data.isAdmin
    saveUserData()
}

export function setAuthToken(newToken: string) {
    userData.authToken = newToken
    saveUserData()
}

export function deleteUserData() {
    userData.isAuthenticated = false
    userData.username = ''
    userData.authToken = ''
    userData.isAdmin = false
    saveUserData()
}

export function loadUserData() {
    /** Load user account data from a local storage */
    const username = localStorage.getItem('userData.username')
    const authToken = localStorage.getItem('userData.authToken')
    const isAdmin = localStorage.getItem('userData.isAdmin') == "true"
    if (isEmpty(username) || isEmpty(authToken)) {
        return
    }
    
    userData.isAuthenticated = true
    userData.username = username
    userData.authToken = authToken
    userData.isAdmin = isAdmin
}

export function saveUserData() {
    setOrDeleteLocalStorage('userData.username', userData.username)
    setOrDeleteLocalStorage('userData.authToken', userData.authToken)
    setOrDeleteLocalStorage('userData.isAdmin', userData.isAdmin.toString())
}

function setOrDeleteLocalStorage(key: string, value: string | null) {
    if (value == null) {
        localStorage.removeItem(key)
    } else {
        localStorage.setItem(key, value)
    }
}