import { reactive } from 'vue'
import { isEmpty } from './StringUtils';

export const userData: UserData = reactive({
    isAuthenticated: false,
    username: 'dupa',
    authToken: '',
    isStaff: false,
})

export interface UserData {
    isAuthenticated: boolean;
    username: string | null;
    authToken: string | null;
    isStaff: boolean;
}

export function setUserData(data: UserData) {
    userData.isAuthenticated = data.isAuthenticated
    userData.username = data.username
    userData.authToken = data.authToken
    userData.isStaff = data.isStaff
    saveUserData()
}

export function deleteUserData() {
    userData.isAuthenticated = false
    userData.username = ''
    userData.authToken = ''
    userData.isStaff = false
    saveUserData()
}

export function loadUserData() {
    /** Load user account data from a local storage */
    const username = localStorage.getItem('userData.username')
    const authToken = localStorage.getItem('userData.authToken')
    const isStaff = localStorage.getItem('userData.isStaff') == "true"
    if (isEmpty(username) || isEmpty(authToken)) {
        return
    }
    
    userData.isAuthenticated = true
    userData.username = username
    userData.authToken = authToken
    userData.isStaff = isStaff
}

export function saveUserData() {
    setOrDeleteLocalStorage('userData.username', userData.username)
    setOrDeleteLocalStorage('userData.authToken', userData.authToken)
    setOrDeleteLocalStorage('userData.isStaff', userData.isStaff.toString())
}

function setOrDeleteLocalStorage(key: string, value: string | null) {
    if (value == null) {
        localStorage.removeItem(key)
    } else {
        localStorage.setItem(key, value)
    }
}