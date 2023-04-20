<script setup lang="ts">
import { reactive, watch, computed, ref, onMounted, type Ref } from 'vue'
import axios from "axios"
import { ToastService } from '@/services/ToastService'
import { AUTH_HEADER } from '@/services/RequestUtils'
import { userData } from '@/services/UserDataStore'
import { DataSet, DataView } from "vis-data";
import { Network, type Options } from "vis-network";


const graphData: GraphData = reactive({
    job_graph: {
        nodes: [],
        edges: [],
    },
})

interface GraphData {
    job_graph: JobGraph
}

interface JobGraph {
    nodes: JobGraphNode[]
    edges: JobGraphEdge[]
}

interface JobGraphNode {
    id: string
    type: string
    title: string
    subtitle?: string
}

interface JobGraphEdge {
    from_id: string
    to_id: string
}

function fetchGraph() {
    axios.get(`/api/job/graph`, {
        headers: {
            [AUTH_HEADER]: userData.authToken,
        },
    }).then(response => {

        const data: GraphData = response.data
        graphData.job_graph = data.job_graph

    }).catch(err => {
        ToastService.showRequestError(`Failed to fetch a jobs graph`, err)
    })
}

fetchGraph()

onMounted(() => {
    initVisNetwork()
})

watch(graphData, () => {
    initVisNetwork()
})

function shapeOfNodeByType(nodeType: string) {
    if (nodeType == 'esc')
        return 'box'
    return 'ellipse'
}

function colorOfNodeByType(nodeType: string) {
    if (nodeType == 'esc')
        return '#97C2FC'
    return '#7BE141'
}

const graphContainerRef: Ref<HTMLElement | null> = ref(null)
const enablePhysicsCheckbox: Ref<HTMLElement | null> = ref(null)

const nodeMapper = (node: JobGraphNode) => ({
    id: node.id,
    label: node.title, 
    title: node.subtitle, 
    shape: shapeOfNodeByType(node.type),
    color: colorOfNodeByType(node.type)
})
const nodeStructs = computed(() =>
    graphData.job_graph.nodes.map(nodeMapper)
)

const edgeMapper = (edge: JobGraphEdge) => ({
    from: edge.from_id,
    to: edge.to_id,
    color: { inherit: "both" },
    arrows: "to",
    title: "has access to",
})
const edgeStructs = computed(() =>
    graphData.job_graph.edges.map(edgeMapper)
)

const focusedNodes: Ref<string[]> = ref([])
const legend: Ref<string> = ref('')
const physics: Ref<boolean> = ref(true)

function showSelectedNodeDetails(nodeId: string) {
    for (var node of nodeStructs.value) {
        if (node.id == nodeId) {
            const subtitle = node.title || ''

            const urlPattern = /(\b(https?):\/\/[-A-Z0-9+&@#\/%?=~_|!:,.;]*[-A-Z0-9+&@#\/%=~_|])/gim;
            const subtitle2 = subtitle.replace(urlPattern, '<a href="$1" target="_blank">$1</a>');
            var nodeDetailsHtml = `
            <div class="card">
                <div class="card-body">
                    <h5>${node.label}</h5>
                    <p style="white-space: pre-line">${subtitle2}</p>
                </div>
            </div>
            `;
            legend.value = nodeDetailsHtml
            return
        }
    }
    legend.value = ''
}

var network: Network | null = null
var networkOptions: Options = {
    nodes: {
        borderWidth: 2,
        shadow: true,
    },
    edges: {
        shadow: true,
        smooth: {
            type: "cubicBezier",
            forceDirection: "none"
        }
    },
    physics: {
        enabled: physics.value,
    },
} as Options

function initVisNetwork() {
    var nodes = new DataSet(nodeStructs.value as any)
    var edges = new DataSet(edgeStructs.value as any)

    const nodesFilter = (node: any) => {
        if (focusedNodes.value.length === 0) {
            return true;
        }
        return focusedNodes.value.includes(node.id);
    }

    const edgesFilter = (edge: any) => {
        return true;
    }

    const nodesView = new DataView(nodes, { filter: nodesFilter });
    const edgesView = new DataView(edges, { filter: edgesFilter });
    var data = {
        nodes: nodesView,
        edges: edgesView,
    };
    console.log('Rendering network graph', data)
    network = new Network(graphContainerRef.value as HTMLElement, data as any, networkOptions)

    network.on("click", function (params) {
        focusedNodes.value = params.nodes
        if (focusedNodes.value.length == 1) {
            // include nodes connected to it
            var mainNodeId = focusedNodes.value[0]
            showSelectedNodeDetails(mainNodeId)
            for (var edge of edgeStructs.value) {
                if (edge.from == mainNodeId) {
                    focusedNodes.value.push(edge.to)
                }
                if (edge.to == mainNodeId) {
                    focusedNodes.value.push(edge.from)
                }
            }
        } else if (focusedNodes.value.length == 0) {
            showSelectedNodeDetails('')
        }
        nodesView.refresh()
    })
}

watch(physics, () => {
    networkOptions.physics.enabled = physics.value
    network?.setOptions(networkOptions)
})
</script>

<template>
    <q-checkbox v-model="physics" label="Enable physics" />
    <div ref="graphContainerRef" style="box-sizing: border-box; height: 640px; border: 1px solid lightgray;"></div>
    <div>{{legend}}</div>
</template>
