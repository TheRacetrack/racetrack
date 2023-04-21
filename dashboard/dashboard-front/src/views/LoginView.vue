<script setup lang="ts">
import { ref } from 'vue'
import { apiClient } from '@/services/ApiClient'
import { toastService } from '@/services/ToastService'
import { setUserData } from '@/services/UserDataStore'
import { useRoute, useRouter, type RouteLocationRaw } from 'vue-router'

const username = ref('')
const password = ref('')
const loading = ref(false)

interface LoginData {
    username: string
    token: string
    is_staff: boolean
}

const router = useRouter()
const route = useRoute()

function login() {
    if (username.value == '') {
        toastService.error(`Username is empty`)
        return
    }
    if (password.value == '') {
        toastService.error(`Password is empty`)
        return
    }

    loading.value = true

    apiClient.post(`/api/accounts/login`,
        {'username': username.value, 'password': password.value},
        false,
    ).then(response => {
        
        loading.value = false
        password.value = ''

        const responseData: LoginData = response.data
        setUserData({
            isAuthenticated: true,
            username: responseData.username,
            authToken: responseData.token,
            isAdmin: responseData.is_staff,
        })

        const nextPath = route.query.next
        if (nextPath) {
            router.push({ path: nextPath } as RouteLocationRaw)
        } else {
            router.push({ name: 'home' })
        }

        toastService.success(`Logged in as ${responseData.username}`)
        
    }).catch(err => {
        toastService.showRequestError(`Login failed`, err)
        loading.value = false
    })
}

function clearCredentials() {
    username.value = ''
    password.value = ''
}
</script>

<template>
  <div class="row justify-center">
    <q-card bordered class="q-pa-lg shadow-1 col-xs-12 col-sm-6 col-md-5">

      <h5 class="text-h5 q-my-sm text-center text-grey-9">Sign In</h5>

      <q-card-section>
        <q-form class="q-gutter-md">
          <q-input outlined autofocus type="email" label="Email" autocomplete="username"
            v-model="username" @keydown.enter.prevent="login"
            >
            <template v-if="username" v-slot:append>
              <q-icon name="cancel" @click.stop.prevent="clearCredentials" class="cursor-pointer" />
            </template>
          </q-input>
          <q-input outlined type="password" label="Password" autocomplete="password"
            v-model="password" @keydown.enter.prevent="login"
            />
        </q-form>
      </q-card-section>
      <q-card-actions class="q-px-md">
        <q-btn color="primary" size="lg" class="full-width" label="Login" push
          :loading="loading" @click="login" />
      </q-card-actions>
      
      <q-separator class="q-ma-sm"/>

      <q-card-section class="text-center q-pa-none">
        <p class="q-pa-sm">
          <router-link :to="{name: 'register'}" class="text-subtitle1 text-primary">Create an account</router-link>
        </p>
        <p class="q-pa-none">
          <router-link :to="{name: 'reset-password'}" class="text-subtitle1 text-primary">Lost password?</router-link>
        </p>
      </q-card-section>

    </q-card>
  </div>
</template>
