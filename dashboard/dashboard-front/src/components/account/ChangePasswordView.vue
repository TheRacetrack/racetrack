<script setup lang="ts">
import { ref } from 'vue'
import { apiClient } from '@/services/ApiClient'
import { toastService } from '@/services/ToastService'

const oldPassword = ref('')
const newPassword = ref('')
const newPassword2 = ref('')
const loading = ref(false)

function changePassword() {
    if (!newPassword.value) {
        toastService.error(`Password cannot be empty`)
        return
    }
    if (newPassword.value !== newPassword2.value) {
        toastService.error(`Passwords do not match`)
        return
    }

    loading.value = true
    apiClient.put(`/api/v1/users/change_password`, {
        'old_password': oldPassword.value, 
        'new_password': newPassword.value,
    }).then(response => {

        loading.value = false
        oldPassword.value = ''
        newPassword.value = ''
        newPassword2.value = ''
        toastService.success(`Your password has been changed.`)
        
    }).catch(err => {
        toastService.showErrorDetails(`Failed to change password`, err)
        loading.value = false
    })
}
</script>

<template>
    <q-card class="q-pa-md">
        <q-card-section>
            <div class="text-h6">
                Change Password
            </div>
        </q-card-section>
        
        <q-card-section class="q-pt-none">
            <q-form class="q-gutter-md">
                <q-input outlined type="password" label="Old password" autocomplete="password"
                    v-model="oldPassword" @keydown.enter.prevent="changePassword"
                />
                <q-input outlined type="password" label="New Password"
                    v-model="newPassword" @keydown.enter.prevent="changePassword"
                />
                <div class="text-grey-7">
                    <ul>
                        <li>Your password can't be too similar to your other personal information.</li>
                        <li>Your password must contain at least 8 characters.</li>
                        <li>Your password can't be a commonly used password.</li>
                        <li>Your password can't be entirely numeric.</li>
                    </ul>
                </div>
                <q-input outlined type="password" label="New password confirmation"
                    hint="Enter the same password as before, for verification."
                    v-model="newPassword2" @keydown.enter.prevent="changePassword"
                />
            </q-form>
        </q-card-section>
        <q-card-actions class="q-px-md">
            <q-btn color="primary" size="md" class="full-width" label="Change password" push
            :loading="loading" @click="changePassword" />
        </q-card-actions>
    </q-card>
</template>
