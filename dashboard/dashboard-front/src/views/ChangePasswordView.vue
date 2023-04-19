<script setup lang="ts">
import { computed } from 'vue';
import { userData } from '@/services/UserDataStore'
import { envInfo } from '@/services/EnvironmentInfo'
import { ToastService } from '@/services/ToastService'
</script>

<template>
  <q-card>
    <q-card-section>
      <div class="text-h6">
        Change Password
      </div>
    </q-card-section>

    <q-card-section class="q-pt-none">

    </q-card-section>
  </q-card>
</template>
