<script setup lang="ts">
import { ref } from 'vue'
import axios from "axios"
import { useRouter } from 'vue-router'
import { ToastService } from '@/services/ToastService';

const username = ref('')
const password = ref('')
const password2 = ref('')
const loading = ref(false)

const router = useRouter()

function register() {
    loading.value = true

    axios.post(`/api/accounts/register`,
        {
            'username': username.value, 
            'password1': password.value,
            'password2': password2.value,
        },
    ).then(response => {
        
        loading.value = false
        password.value = ''
        password2.value = ''

        router.push({ name: 'login' })

        ToastService.success(`Your account "${username.value}" have been registered. Now wait till Racetrack admin activates your account.`)
        
    }).catch(err => {
        ToastService.showRequestError(`Registering failed`, err)
        loading.value = false
    })
}
</script>

<template>
    <div class="row justify-center">
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
              <p class="text-grey-7">
                <ul>
                  <li>Your password can't be too similar to your other personal information.</li>
                  <li>Your password must contain at least 8 characters.</li>
                  <li>Your password can't be a commonly used password.</li>
                  <li>Your password can't be entirely numeric.</li>
                </ul>
              </p>
            <q-input outlined type="password" label="Password confirmation" autocomplete="password"
              hint="Enter the same password as before, for verification."
              v-model="password2" @keydown.enter.prevent="register"
              />
          </q-form>
        </q-card-section>
        <q-card-actions class="q-px-md">
          <q-btn color="primary" size="md" class="full-width" label="Register"
            :loading="loading" @click="register" />
        </q-card-actions>

      </q-card>
    </div>
</template>
