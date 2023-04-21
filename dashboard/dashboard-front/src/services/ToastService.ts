import { TYPE, useToast } from "vue-toastification"
import type { ToastContent, ToastID, ToastOptions } from "vue-toastification/dist/types/types"

type _ToastOptions = ToastOptions & {type?: any}
type ToasterFunction = (content: ToastContent, options?: _ToastOptions | undefined) => ToastID

export class ToastService {

    toast = useToast()

    lastToastId: ToastID | null = null
    lastToastMessage: string | null = null

    info(msg: string): ToastID {
        return this.showToast(msg, this.toast.info, 5000, true, "top-right")
    }

    error(msg: string): ToastID {
        return this.showToast(msg, this.toast.error, 7000, false, "top-center")
    }

    success(msg: string): ToastID {
        return this.showToast(msg, this.toast.success, 3000, true, "top-right")
    }

    warning(msg: string): ToastID {
        return this.showToast(msg, this.toast.warning, 5000, true, "top-right")
    }

    notify(msg: string): ToastID {
        return this.showToast(msg, this.toast.success, 15000, false, "top-center")
    }

    showToast(
        msg: string, toaster: ToasterFunction,
        timeout: number = 5000, closeOnClick: boolean = true, position: string = "top-right",
    ): ToastID {
        if (this.lastToastId !== null && this.lastToastMessage == msg) {
            this.toast.dismiss(this.lastToastId)
        }

        const options = {
            position: position,
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
        return this.lastToastId
    }

    showRequestError(context: string, err: any) {
        console.error(`Request error: ${context}: ${err}`)
        if (err.response !== undefined) {
            if (err.response.hasOwnProperty('data')){
                const data = err.response.data
                if (data !== undefined && data.hasOwnProperty('error')){
                    const errorDetails = data.error
                    this.error(`${context}: ${errorDetails}`)
                    return
                }
            }
        }
        this.error(`${context}: ${err}`)
    }
}

export const toastService: ToastService = new ToastService()
