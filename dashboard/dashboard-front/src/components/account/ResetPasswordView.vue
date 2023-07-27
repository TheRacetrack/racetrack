<script setup lang="ts">

</script>

<template>
    <div class="row justify-center app-container">
      <q-card bordered class="q-pa-lg full-width">

        <h5 class="text-h5 q-my-sm text-center text-grey-9">Forgot Your Password?</h5>
        <p>Please contact your Racetrack administrator for help.</p>

        <q-card-section class="text-center q-pa-none">
            <p class="q-pt-sm"><router-link :to="{name: 'login'}" class="text-subtitle1 text-primary">Sign in</router-link></p>
        </q-card-section>

      </q-card>
    </div>
</template>
