<script setup lang="ts">
import { computed } from 'vue'
import { copyToClipboard } from 'quasar'
import { userData, setAuthToken } from '@/services/UserDataStore'
import { envInfo } from '@/services/EnvironmentInfo'
import { toastService } from '@/services/ToastService'
import { apiClient } from '@/services/ApiClient'

function copyAuthToken() {
    copyToClipboard(userData.authToken || '')
        .then(() => {
            toastService.success(`Auth Token copied to clipboard.`)
        }).catch((error) => {
            toastService.error(`Failed to copy to clipboard.`)
        })
}

const loginCommand = computed(() => 
    `racetrack login --remote ${envInfo.lifecycle_url} ${userData.authToken}`
)

function copyLoginCommand() {
    copyToClipboard(loginCommand.value)
    .then(() => {
        toastService.success(`Command copied to clipboard.`)
    })
    .catch((error) => {
        toastService.error(`Failed to copy to clipboard.`)
    })
}

function regenerateToken() {
    apiClient.post(`/api/accounts/token/regenerate`).then(response => {
        setAuthToken(response.data.new_token)
        toastService.success(`Token regenerated.`)
    }).catch(err => {
        toastService.showErrorDetails(`Failed to regenerate token`, err)
    })
}
</script>

<template>
    <q-card>
        <q-card-section>
            <div class="text-h6">
                User Profile
                <q-badge color="primary" v-if="userData.isAdmin">admin</q-badge>
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
                    <span class="x-monospace x-overflow-any">
                        {{ userData.authToken }}
                    </span>
                </template>
                <template v-slot:append>
                    <q-btn round dense flat icon="content_copy" @click="copyAuthToken" />
                </template>
            </q-field>
            
            <p class="q-mt-md">
                Run this in CLI to deploy Jobs to this Racetrack:
                <q-field filled dense>
                    <template v-slot:control>
                        <div class="x-monospace x-overflow-any">
                            {{ loginCommand }}
                        </div>
                    </template>
                    <template v-slot:append>
                        <q-btn round dense flat icon="content_copy" @click="copyLoginCommand" />
                    </template>
                </q-field>
            </p>
            
            <q-btn-group push>
                <q-btn color="primary" push label="Change Password" icon="key" :to="{name: 'change-password'}" />
                <q-btn color="primary" push label="Regenerate Token" icon="autorenew" @click="regenerateToken" />
            </q-btn-group>
            
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
                <q-field filled dense>
                    <template v-slot:control>
                        <div class="x-monospace">
                            {{ envInfo.lifecycle_url }}
                        </div>
                    </template>
                </q-field>
            </p>
            
            <p>
                To add it as alias, run:
                <q-field filled dense>
                    <template v-slot:control>
                        <div class="x-monospace">
                            racetrack set alias ALIAS_NAME {{ envInfo.lifecycle_url }}
                        </div>
                    </template>
                </q-field>
            </p>
            
            <p>
                To set the current remote, run:
                <q-field filled dense>
                    <template v-slot:control>
                        <div class="x-monospace">
                            racetrack set remote {{ envInfo.lifecycle_url }}
                        </div>
                    </template>
                </q-field>
            </p>
            
            <p>
                To deploy here, run:
                <q-field filled dense>
                    <template v-slot:control>
                        <div class="x-monospace">
                            racetrack deploy MANIFEST_PATH --remote {{ envInfo.lifecycle_url }}
                        </div>
                    </template>
                </q-field>
            </p>
            
        </q-card-section>
    </q-card>
</template>
