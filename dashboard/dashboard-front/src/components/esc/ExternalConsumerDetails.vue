<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import {copyToClipboard} from "quasar"
import { type QTableProps } from 'quasar'
import {type EscAuthData, type AuthTokenData} from '@/utils/api-schema'
import { formatDateIso8601 } from '@/utils/time'
import { toastService } from '@/services/ToastService'
import { apiClient } from '@/services/ApiClient'
import {progressService} from "@/services/ProgressService"
import XTooltip from "@/components/XTooltip.vue"

const route = useRoute()
const escId = route.params.escId
const escData = ref<EscAuthData | null>(null)

function fetchESCData() {
    apiClient.get<EscAuthData>(`/api/v1/escs/${escId}/auth_data`)
        .then(response => {
            escData.value = response.data
        }).catch(err => {
            toastService.showErrorDetails(`Failed to fetch ESC details`, err)
        })
}

onMounted(() => {
    fetchESCData()
})

function copyAuthToken(authToken: AuthTokenData) {
    copyToClipboard(authToken.token)
        .then(() => {
            toastService.success(`Auth Token copied to clipboard.`)
        }).catch(err => {
            toastService.showErrorDetails(`Failed to copy to clipboard.`, err)
        })
}

function revokeAuthToken(authToken: AuthTokenData) {
    progressService.confirmWithLoading({
        confirmQuestion: `Are you sure you want to revoke the token "${authToken.token}"?`,
        onConfirm: () => {
            return apiClient.delete(`/api/v1/escs/${escId}/auth_token/${authToken.id}`)
        },
        progressMsg: `Revoking token…`,
        successMsg: `Token has been revoked.`,
        errorMsg: `Failed to revoke the token`,
        onSuccess: () => {
            fetchESCData()
        },
    })
}

const authTokensColumns: QTableProps['columns'] = [
    {
        name: 'token',
        label: 'Token string (X-Racetrack-Auth)',
        align: 'left',
        field: (row: AuthTokenData) => row.token,
    },
    {
        name: 'expires-at',
        label: 'Expires at',
        align: 'right',
        field: (row: AuthTokenData) => row.expiry_time,
        format: (val: number) => formatDateIso8601(val),
    },
    {
        name: 'active',
        label: 'Active',
        align: 'right',
        field: (row: AuthTokenData) => row.active,
        format: (val: boolean) => val ? 'Yes' : 'No',
    },
    {
        name: 'last-used-at',
        label: 'Last used at',
        align: 'right',
        field: (row: AuthTokenData) => row.last_use_time,
        format: (val: number) => formatDateIso8601(val),
    },
    {
        name: 'actions',
        label: 'Actions',
        align: 'left',
        field: (_: AuthTokenData) => "",
    },
]
</script>

<template>
    <q-card>
        <q-card-section>
            <div class="text-h6">External Service Consumer Details</div>
        </q-card-section>

        <q-card-section>
            <q-field outlined label="ID" stack-label>
                <template v-slot:control>
                    {{ escData?.id }}
                </template>
            </q-field>

            <q-field outlined label="Name" stack-label>
                <template v-slot:control>
                    <div>{{ escData?.name }}</div>
                </template>
            </q-field>

            <q-table
                flat bordered hide-pagination
                title="Auth Tokens"
                :rows="escData?.tokens || []"
                :columns="authTokensColumns"
                row-key="token"
                no-data-label="No auth tokens"
            >
                <template v-slot:body-cell-actions="props">
                    <q-td :props="props">
                        <q-btn round dense flat icon="content_copy" @click="copyAuthToken(props.row)">
                            <XTooltip>Copy token to clipboard</XTooltip>
                        </q-btn>
                        <q-btn round dense flat icon="clear" @click="revokeAuthToken(props.row)">
                            <XTooltip>Revoke token</XTooltip>
                        </q-btn>
                    </q-td>
                </template>
                <template v-slot:body-cell-token="props">
                    <q-td :props="props">
                        <div class="x-monospace x-overflow-any" style="max-width: 50vw; white-space: normal;">
                            {{ props.row.token }}
                        </div>
                    </q-td>
                </template>
            </q-table>

        </q-card-section>
    </q-card>
</template>