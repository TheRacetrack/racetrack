import type { Ref } from 'vue'
import type ProgressComponent from '@/components/ProgressComponent.vue'


export class ProgressService {
    
    progressCompononentRef: Ref<typeof ProgressComponent | null> | null = null

    init(progressCompononentRef: Ref<typeof ProgressComponent | null>) {
        this.progressCompononentRef = progressCompononentRef
    }

    showDialog(body: string): Promise<boolean> {
        return new Promise((resolve, reject) => {
            this.progressCompononentRef?.value?.showDialog(body, resolve)
        })
    }

    startProgressLoading() {
        this.progressCompononentRef?.value?.startLoading()
    }

    stopProgressLoading() {
        this.progressCompononentRef?.value?.stopLoading()
    }
}

export const progressService: ProgressService = new ProgressService()
