<script setup lang="ts">
import { userData } from '@/services/UserDataStore.js'
</script>

<template>
  <h1>Profile</h1>

  <p>
    Username: <span>{{ userData.username }}</span>
  </p>
  <p>
    Auth Token: <span>{{ userData.authToken }}</span>
  </p>
  <p>
    Admin: <span>{{ userData.isStaff ? 'yes' : 'no' }}</span>
  </p>
</template>
