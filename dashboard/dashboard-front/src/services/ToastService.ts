import { useToast } from "vue-toastification"
import type { ToastID } from "vue-toastification/dist/types/types";

export class ToastService {

    static toast = useToast();

    static lastSuccessToastId: ToastID | null = null;

    static toastInfo(msg: string) {
        console.log(`Toast info: ${msg}`);
        this.toast.info(msg, {
            position: "top-right",
            timeout: 5000,
            closeOnClick: true,
            pauseOnFocusLoss: true,
            pauseOnHover: true,
            draggable: false,
            hideProgressBar: false,
            closeButton: "button",
        } as any);
    }

    static toastError(msg: string) {
        console.log(`Toast error: ${msg}`);
        this.toast.error(msg, {
            position: "top-right",
            timeout: 7000,
            closeOnClick: false,
            pauseOnFocusLoss: true,
            pauseOnHover: true,
            draggable: false,
            hideProgressBar: false,
            closeButton: "button",
        } as any);
    }

    static toastSuccess(msg: string) {
        if (this.lastSuccessToastId) {
            this.toast.dismiss(this.lastSuccessToastId);
        }

        console.log(`Toast success: ${msg}`);
        this.lastSuccessToastId = this.toast.success(msg, {
            position: "top-right",
            timeout: 3000,
            closeOnClick: true,
            pauseOnFocusLoss: true,
            pauseOnHover: true,
            draggable: false,
            hideProgressBar: false,
            closeButton: "button",
        } as any);
    }

    static showRequestError(context: string, err: any) {
        console.error(`Request error: ${context}: ${err}`);
        if (err.response !== undefined) {
            if (err.response.hasOwnProperty('data')){
                const data = err.response.data
                if (data !== undefined && data.hasOwnProperty('error')){
                    const errorDetails = data.error
                    this.toastError(`${context}: ${errorDetails}`);
                    return
                }
            }
        }
        this.toastError(`${context}: ${err}`);
    }
}
