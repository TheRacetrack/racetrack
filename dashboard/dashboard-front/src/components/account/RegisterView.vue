<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { apiClient } from '@/services/ApiClient'
import { toastService } from '@/services/ToastService'

const username = ref('')
const password = ref('')
const password2 = ref('')
const loading = ref(false)

const router = useRouter()

function register() {
    if (!password.value) {
        toastService.error(`Password cannot be empty`)
        return
    }
    if (password.value !== password2.value) {
        toastService.error(`Passwords do not match`)
        return
    }

    loading.value = true
    apiClient.post(`/api/v1/users/register`,
        {
            'username': username.value, 
            'password': password.value,
        },
        false,
    ).then(response => {
        
        loading.value = false
        password.value = ''
        password2.value = ''
        
        router.push({ name: 'login' })
        toastService.notify(`Your account "${username.value}" have been registered. Now wait till Racetrack admin activates your account.`)
        
    }).catch(err => {
        toastService.showErrorDetails(`Registering failed`, err)
        loading.value = false
    })
}
</script>

<template>
    <div class="app-container">
    <q-card bordered class="q-pa-md full-width">
        
        <h5 class="text-h5 q-my-sm text-center text-grey-9">Create an account</h5>
        
        <q-card-section>
            <q-form class="q-gutter-md">
                <q-input outlined autofocus type="email" label="Email" autocomplete="username"
                hint="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only. Use your email as username."
                v-model="username" @keydown.enter.prevent="register"
                />
                <q-input outlined type="password" label="Password" autocomplete="password"
                v-model="password" @keydown.enter.prevent="register"
                />
                <div class="text-grey-7">
                    <ul>
                        <li>Your password can't be too similar to your other personal information.</li>
                        <li>Your password must contain at least 8 characters.</li>
                        <li>Your password can't be a commonly used password.</li>
                        <li>Your password can't be entirely numeric.</li>
                    </ul>
                </div>
                <q-input outlined type="password" label="Password confirmation" autocomplete="password"
                hint="Enter the same password as before, for verification."
                v-model="password2" @keydown.enter.prevent="register"
                />
            </q-form>
        </q-card-section>
        <q-card-actions class="q-px-md">
            <q-btn color="primary" size="md" class="full-width" label="Register" push
            :loading="loading" @click="register" />
        </q-card-actions>

        <q-separator class="q-ma-sm"/>

        <q-card-section class="text-center q-pa-none">
            <p class="q-pt-sm"><router-link :to="{name: 'login'}" class="text-subtitle1 text-primary">Sign in</router-link></p>
        </q-card-section>
        
    </q-card>
    </div>
</template>
