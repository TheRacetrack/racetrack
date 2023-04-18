<script setup lang="ts">
import { copyToClipboard } from 'quasar'
import { userData } from '@/services/UserDataStore'
import { envInfo } from '@/services/EnvironmentInfo'
import { ToastService } from '@/services/ToastService'

function copyAuthToken() {
  copyToClipboard(userData.authToken || '')
    .then(() => {
      ToastService.success(`Auth Token copied to clipboard.`)
    })
    .catch((error) => {
      ToastService.error(`Failed to copy to clipboard.`)
    })
}
</script>

<template>
  <q-card>
    <q-card-section>
      <div class="text-h6">
        User Profile

        <q-badge color="primary" v-if="userData.isAdmin">
            admin
        </q-badge>
      </div>
    </q-card-section>

    <q-card-section class="q-pt-none">

      <q-field outlined label="Username" stack-label>
        <template v-slot:control>
          <div>{{ userData.username }}</div>
        </template>
      </q-field>

      <q-field outlined label="Auth Token" stack-label class="q-mt-md">
        <template v-slot:control>
          <span style="overflow-wrap: anywhere;">
            {{ userData.authToken }}
          </span>
        </template>
        <template v-slot:append>
          <q-btn round dense flat icon="content_copy" @click="copyAuthToken" />
        </template>
      </q-field>

    </q-card-section>
  </q-card>

  <q-separator class="q-my-md" inset/>

  <q-card>
    <q-card-section>
      <div class="text-h6">Info</div>
    </q-card-section>
    <q-card-section class="q-pt-none">

      <p>
        Racetrack's remote address: 
        <a :href="envInfo.lifecycle_url" target="_blank"> {{ envInfo.lifecycle_url }}</a>
      </p>

      <p>
        To add it as alias, run:
        <q-field filled dense>
          <template v-slot:control>
            <div class="self-center full-width no-outline" tabindex="0" style="font-family: monospace;">
              racetrack set alias ALIAS_NAME {{ envInfo.lifecycle_url }}
            </div>
          </template>
        </q-field>
      </p>
      
      <p>
        To set the current remote, run:
        <q-field filled dense>
          <template v-slot:control>
            <div class="self-center full-width no-outline" tabindex="0" style="font-family: monospace;">
              racetrack set remote {{ envInfo.lifecycle_url }}
            </div>
          </template>
        </q-field>
      </p>
      
      <p>
        To deploy here, run:
        <q-field filled dense>
          <template v-slot:control>
            <div class="self-center full-width no-outline" tabindex="0" style="font-family: monospace;">
              racetrack deploy MANIFEST_PATH --remote {{ envInfo.lifecycle_url }}
            </div>
          </template>
        </q-field>
      </p>

    </q-card-section>
  </q-card>
</template>
