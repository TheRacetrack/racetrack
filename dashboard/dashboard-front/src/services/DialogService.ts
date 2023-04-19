import { type Ref } from 'vue'
import ConfirmationDialog from '@/components/ConfirmationDialog.vue'


export class DialogService {
    
    static confirmDialogRef: Ref<typeof ConfirmationDialog | null> | null

    static init(confirmDialogRef: Ref<typeof ConfirmationDialog | null>) {
        this.confirmDialogRef = confirmDialogRef
    }

    static showDialog(body: string, callback: () => void) {
        this.confirmDialogRef?.value?.showDialog(body, callback)
    }

    static startLoading() {
        this.confirmDialogRef?.value?.startLoading()
    }

    static stopLoading() {
        this.confirmDialogRef?.value?.stopLoading()
    }
}
