import { TYPE, useToast } from "vue-toastification"
import type { ToastContent, ToastID, ToastOptions } from "vue-toastification/dist/types/types"

type _ToastOptions = ToastOptions & {type?: any}
type ToasterFunction = (content: ToastContent, options?: _ToastOptions | undefined) => ToastID

export class ToastService {

    static toast = useToast()

    static lastToastId: ToastID | null = null
    static lastToastMessage: string | null = null

    static toastInfo(msg: string) {
        this.showToast(msg, this.toast.info, 5000)
    }

    static toastError(msg: string) {
        this.showToast(msg, this.toast.error, 7000, false)
    }

    static toastSuccess(msg: string) {
        this.showToast(msg, this.toast.success, 3000)
    }

    static toastWarning(msg: string) {
        this.showToast(msg, this.toast.warning, 5000)
    }

    static showToast(msg: string, toaster: ToasterFunction, timeout: number = 5000, closeOnClick: boolean = true) {
        if (this.lastToastId !== null && this.lastToastMessage == msg) {
            this.toast.dismiss(this.lastToastId)
        }

        const options = {
            position: "top-right",
            timeout: timeout,
            closeOnClick: closeOnClick,
            pauseOnFocusLoss: true,
            pauseOnHover: true,
            draggable: false,
            hideProgressBar: false,
            closeButton: "button",
        } as _ToastOptions

        this.lastToastMessage = msg
        this.lastToastId = toaster(msg, options)
        console.log(`Toast: ${msg}`)
    }

    static showRequestError(context: string, err: any) {
        console.error(`Request error: ${context}: ${err}`)
        if (err.response !== undefined) {
            if (err.response.hasOwnProperty('data')){
                const data = err.response.data
                if (data !== undefined && data.hasOwnProperty('error')){
                    const errorDetails = data.error
                    this.toastError(`${context}: ${errorDetails}`)
                    return
                }
            }
        }
        this.toastError(`${context}: ${err}`)
    }
}
