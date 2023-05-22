import type { Ref } from 'vue'
import type ProgressComponent from '@/components/ProgressComponent.vue'
import { toastService } from '@/services/ToastService'


interface ConfirmWithLoadingOptions {
    confirmQuestion: string
    progressMsg: string
    successMsg: string
    errorMsg: string
    onConfirm: () => Promise<any>
    onSuccess?: (response: any) => void
    onFinalize?: () => void
}

interface RunLoadingOptions {
    task: Promise<any>
    loadingState?: Ref<boolean>
    progressMsg: string
    successMsg?: string
    errorMsg: string
    onSuccess?: (response: any) => void
    onFinalize?: () => void
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
        {confirmQuestion, progressMsg, successMsg, errorMsg, onConfirm, onSuccess, onFinalize}: ConfirmWithLoadingOptions
    ) {
        this.showDialog(confirmQuestion)
            .then(() => {
                this.startLoadingProgress()
                toastService.loading(progressMsg)
                return onConfirm()

            }).finally(() => {
                toastService.dismissLoading()
                
            }).then((response: any) => {
                onSuccess?.(response)
                toastService.success(successMsg)

            }).catch((err: any) => {
                toastService.showErrorDetails(errorMsg, err)

            }).finally(() => {
                this.stopLoadingProgress()
                toastService.dismissLoading()
                onFinalize?.()
            })
    }

    runLoading(
        {task, loadingState, progressMsg, successMsg, errorMsg, onSuccess, onFinalize}: RunLoadingOptions
    ) {
        toastService.loading(progressMsg)
        if (loadingState != null)
            loadingState.value = true
        this.startLoadingProgress()

        task.finally(() => {
                toastService.dismissLoading()
                if (loadingState != null)
                    loadingState.value = false
                this.stopLoadingProgress()
                onFinalize?.()
                
            }).then((response: any) => {
                onSuccess?.(response)
                if (successMsg)
                    toastService.success(successMsg)

            }).catch((err: any) => {
                toastService.showErrorDetails(errorMsg, err)
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
