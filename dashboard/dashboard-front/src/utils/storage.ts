import { type Ref, watch } from 'vue'

export function rememberInLocalStorage<T>(variableRef: Ref<T>, key: string) {

    const storedVar = localStorage.getItem(key)
    if (storedVar != null) {
        try {
            variableRef.value = JSON.parse(storedVar) as T
        } catch(e) {
            console.error(e)
        }
    }

    watch(variableRef, () => {
        localStorage.setItem(key, JSON.stringify(variableRef.value))
    })
}
