<script setup lang="ts">
import { ref } from 'vue'
import axios from "axios"
import { ToastService } from '@/services/ToastService';
import { setUserData } from '@/services/UserDataStore.js';
import router from '@/router';
import { useRoute } from 'vue-router';

const email = ref('')
const password = ref('')
const loading = ref(false)

interface LoginData {
    username: string;
    token: string;
    is_staff: boolean;
}

const route = useRoute()
const nextPath = route.query.next

if (nextPath) {
  ToastService.toastInfo(`Please log in to see this page.`)
}

function login() {
    loading.value = true

    axios.post(`/api/accounts/login`,
        {'username': email.value, 'password': password.value},
    ).then(response => {
        
        loading.value = false
        password.value = ''

        const responseData: LoginData = response.data
        setUserData({
            isAuthenticated: true,
            username: responseData.username,
            authToken: responseData.token,
            isStaff: responseData.is_staff,
        })

        if (nextPath) {
            router.push({ path: nextPath })
        } else {
            router.push({ name: 'home' })
        }

        ToastService.toastSuccess(`Logged in as ${responseData.username}`)
        
    }).catch(err => {
        ToastService.showRequestError(`Login failed`, err)
        loading.value = false
    })
}
</script>

<template>
    <div class="row justify-center">
      <q-card bordered class="q-pa-lg shadow-1 col-xs-12 col-sm-6 col-md-4">

        <h5 class="text-h5 q-my-sm text-center text-grey-9">Sign In</h5>

        <q-card-section>
          <q-form class="q-gutter-md">
            <q-input outlined autofocus type="email" label="Email" autocomplete="username"
              v-model="email" @keydown.enter.prevent="login"
              >
              <template v-if="email" v-slot:append>
                <q-icon name="cancel" @click.stop.prevent="email = ''" class="cursor-pointer" />
              </template>
            </q-input>
            <q-input outlined type="password" label="Password" autocomplete="password"
              v-model="password" @keydown.enter.prevent="login"
              />
          </q-form>
        </q-card-section>
        <q-card-actions class="q-px-md">
          <q-btn color="primary" size="lg" class="full-width" label="Login"
            :loading="loading" @click="login" />
        </q-card-actions>
        
        <q-separator class="q-ma-sm"/>

        <q-card-section class="text-center q-pa-none">
          <p class="q-pa-sm">
              <a href="/register">Create an account</a>
          </p>
          <p class="q-pa-none">
              <a>Lost password?</a>
          </p>
        </q-card-section>

      </q-card>
    </div>
</template>
