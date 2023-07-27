import { AxiosError } from "axios"
import { useToast } from "vue-toastification"
import type { ToastContent, ToastID, ToastOptions } from "vue-toastification/dist/types/types"
import { extractErrorDetails } from "@/utils/error"
import LoadingSpinner from '@/components/LoadingSpinner.vue'

type _ToastOptions = ToastOptions & {type?: any}
type ToasterFunction = (content: ToastContent, options?: _ToastOptions | undefined) => ToastID

export class ToastService {

    toast = useToast()

    lastToastId: ToastID | null = null
    lastToastMessage: string | null = null
    loadingToastId: ToastID | null = null

    info(msg: string): ToastID {
        return this.showToast(msg, this.toast.info, 5000, true, "top-right")
    }

    error(msg: string): ToastID {
        return this.showToast(msg, this.toast.error, 20000, false, "top-center")
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

    loading(msg: string): ToastID {
        this.loadingToastId = this.showToast(msg, this.toast.info, 0, true, "top-right", true)
        return this.loadingToastId
    }

    showToast(
        msg: string, toaster: ToasterFunction,
        timeout: number = 5000, closeOnClick: boolean = true, position: string = "top-right",
        loadingIcon: boolean = false,
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

        if (loadingIcon) {
            options.icon = LoadingSpinner
        }

        this.lastToastMessage = msg
        this.lastToastId = toaster(msg, options)
        console.log(`Toast: ${msg}`)
        return this.lastToastId
    }

    showErrorDetails(context: string, err: any) {
        const errDetails = extractErrorDetails(err)
        if (err instanceof AxiosError) {
            console.error(`Request Error: ${context}: ${err.message}`)
        } else {
            console.error(`Error: ${context}: ${err}`)
        }
        this.error(`${context}: ${errDetails}`)
    }

    dismiss(id: ToastID) {
        this.toast.dismiss(id)
    }

    dismissLoading() {
        if (this.loadingToastId != null)
            this.toast.dismiss(this.loadingToastId)
    }
}

export const toastService: ToastService = new ToastService()
