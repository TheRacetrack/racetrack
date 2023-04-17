<script setup lang="ts">
import { ref } from 'vue'

const email = ref('')
const password = ref('')
const loading = ref(false)

function login() {
  loading.value = true
}
</script>

<template>
    <div class="row justify-center">
      <q-card bordered class="q-pa-lg shadow-1 col-xs-12 col-sm-6 col-md-4">

        <h5 class="text-h5 q-my-sm text-center text-grey-9">Sign In</h5>

        <q-card-section>
          <q-form class="q-gutter-md">
            <q-input outlined autofocus type="email" label="Email"
              v-model="email" @keydown.enter.prevent="login"
              >
              <template v-if="email" v-slot:append>
                <q-icon name="cancel" @click.stop.prevent="email = ''" class="cursor-pointer" />
              </template>
            </q-input>
            <q-input outlined type="password" label="Password"
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
