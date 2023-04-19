<script setup lang="ts">
import { reactive, onUpdated, computed } from 'vue'
import axios from "axios"
import { ToastService } from '@/services/ToastService'
import { formatTimestampIso8601 } from '@/services/DateUtils'
import { AUTH_HEADER } from '@/services/RequestUtils'
import { userData } from '@/services/UserDataStore'
import { DialogService } from '@/services/DialogService'
import { DataSet, DataView } from "vis-data";
import { Network } from "vis-network";


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

onUpdated(() => {
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

const nodeMapper = (node: JobGraphNode) => ({
    id: node.id,
    label: node.title, 
    title: node.subtitle, 
    shape: shapeOfNodeByType(node.type),
    color: colorOfNodeByType(node.type)
})

var nodeStructs = computed(() => 
    graphData.job_graph.nodes.map(nodeMapper)
)

var nodes = new DataSet(nodeStructs as any)

const edgeMapper = (edge: JobGraphEdge) => ({
    from: edge.from_id,
    to: edge.to_id,
    color: { inherit: "both" },
    arrows: "to",
    title: "has access to",
})

var edgeStructs = computed(() =>
    graphData.job_graph.edges.map(edgeMapper)
)

var edges = new DataSet(edgeStructs as any)

var focusedNodes: string[] = []

const nodesFilter = (node: any) => {
    if (focusedNodes.length === 0) {
        return true;
    }
    return focusedNodes.includes(node.id);
}

const edgesFilter = (edge: any) => {
    return true;
}

function initVisNetwork() {
    const nodesView = new DataView(nodes, { filter: nodesFilter });
    const edgesView = new DataView(edges, { filter: edgesFilter });
    var data = {
        nodes: nodesView,
        edges: edgesView,
    };
    var options = {
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
            enabled: true,
        },
    }
    var container = document.getElementById("graph-area") as HTMLElement
    var network = new Network(container, data as any, options as any)
}

// network.on("click", function (params) {
//     focusedNodes = params.nodes;
//     if (focusedNodes.length == 1) {
//         // include nodes connected to it
//         var mainNodeId = focusedNodes[0];
//         showSelectedNodeDetails(mainNodeId)
//         for (var edge of edgeStructs) {
//             if (edge.from == mainNodeId) {
//                 focusedNodes.push(edge.to);
//             }
//             if (edge.to == mainNodeId) {
//                 focusedNodes.push(edge.from);
//             }
//         }
//     } else if (focusedNodes.length == 0) {
//         showSelectedNodeDetails('')
//     }
//     nodesView.refresh();
// });

// function showSelectedNodeDetails(nodeId) {
//     for (var node of nodeStructs) {
//         if (node.id == nodeId) {
//             subtitle = node.title;

//             urlPattern = /(\b(https?):\/\/[-A-Z0-9+&@#\/%?=~_|!:,.;]*[-A-Z0-9+&@#\/%=~_|])/gim;
//             subtitle = subtitle.replace(urlPattern, '<a href="$1" target="_blank">$1</a>');
//             var nodeDetailsHtml = `
//             <div class="card">
//                 <div class="card-body">
//                     <h5>${node.label}</h5>
//                     <p style="white-space: pre-line">${subtitle}</p>
//                 </div>
//             </div>
//             `;
//             $('#graph-area-legend').html(nodeDetailsHtml);
//             return;
//         }
//     }
//     $('#graph-area-legend').html('');
// }

// document.getElementById("enablePhysicsCheckbox").addEventListener("change", (e) => {
//     const { value, checked } = e.target;
//     options.physics.enabled = checked;
//     network.setOptions(options);
// })
</script>

<template>
    <label><input type="checkbox" id="enablePhysicsCheckbox" value="true" checked />Enable physics</label>
    <div id="graph-area" style="box-sizing: border-box; height: 640px; border: 1px solid lightgray;"></div>
    <div id="graph-area-legend"></div>
</template>
