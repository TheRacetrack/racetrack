import type { Ref } from 'vue'
import type ProgressComponent from '@/components/ProgressComponent.vue'
import { toastService } from '@/services/ToastService'


interface ConfirmWithLoadingOptions {
    confirmQuestion: string
    progressMsg: string
    successMsg: string
    errorMsg: string
    onConfirm: () => Promise<any>
    onSuccess: (response: any) => void
    onFinally?: () => void
}

export class ProgressService {
    
    progressCompononentRef: Ref<typeof ProgressComponent | null> | null = null

    init(progressCompononentRef: Ref<typeof ProgressComponent | null>) {
        this.progressCompononentRef = progressCompononentRef
    }

    showDialog(body: string): Promise<void> {
        return new Promise((resolve, reject) => {
            this.progressCompononentRef?.value?.showDialog(body, resolve)
        })
    }

    confirmWithLoading(
        {confirmQuestion, progressMsg, successMsg, errorMsg, onConfirm, onSuccess, onFinally}: ConfirmWithLoadingOptions
    ) {
        this.showDialog(confirmQuestion)
            .then(() => {
                this.startLoadingProgress()
                toastService.loading(progressMsg)
                return onConfirm()

            }).finally(() => {
                toastService.dismissLoading()
                
            }).then((response: any) => {
                onSuccess(response)
                toastService.success(successMsg)

            }).catch((err: any) => {
                toastService.showErrorDetails(errorMsg, err)

            }).finally(() => {
                this.stopLoadingProgress()
                toastService.dismissLoading()
                onFinally?.()
            })
    }

    startLoadingProgress() {
        this.progressCompononentRef?.value?.startLoading()
    }

    stopLoadingProgress() {
        this.progressCompononentRef?.value?.stopLoading()
    }
}

export const progressService: ProgressService = new ProgressService()
