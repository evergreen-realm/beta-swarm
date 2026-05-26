// brain.js - D3.js Force Directed Graph renderer for the Hybrid Brain

let svg, simulation;

function initBrainGraph() {
    const container = document.getElementById('brain-graph');
    if (!container) return;
    
    // Clear previous SVG
    container.innerHTML = '';
    
    const width = container.clientWidth || 800;
    const height = container.clientHeight || 400;
    
    svg = d3.select('#brain-graph')
        .append('svg')
        .attr('width', '100%')
        .attr('height', '100%')
        .attr('viewBox', `0 0 ${width} ${height}`)
        .append('g');
        
    // Zoom behavior
    d3.select('#brain-graph svg').call(d3.zoom().on('zoom', (event) => {
        svg.attr('transform', event.transform);
    }));

    // Seed nodes representing knowledge categories
    const graphData = {
        nodes: [
            { id: 'hybrid_brain', group: 1, label: 'Hybrid Brain Core', r: 12 },
            { id: 'letta_memory', group: 2, label: 'Letta (MemGPT) LTM', r: 8 },
            { id: 'cognee_graph', group: 3, label: 'Cognee Graph Layers', r: 8 },
            { id: 'kuzu_db', group: 4, label: 'KuzuDB Local Triples', r: 10 },
            { id: 'neo4j_global', group: 5, label: 'Neo4j Global Graph', r: 10 },
            { id: 'obsidian_vault', group: 6, label: 'Obsidian Notes', r: 8 },
            { id: 'stage_deploy', group: 7, label: 'Stage 9 Synthesis', r: 6 }
        ],
        links: [
            { source: 'hybrid_brain', target: 'letta_memory' },
            { source: 'hybrid_brain', target: 'cognee_graph' },
            { source: 'hybrid_brain', target: 'kuzu_db' },
            { source: 'hybrid_brain', target: 'neo4j_global' },
            { source: 'kuzu_db', target: 'neo4j_global' },
            { source: 'letta_memory', target: 'obsidian_vault' },
            { source: 'stage_deploy', target: 'kuzu_db' }
        ]
    };

    simulation = d3.forceSimulation(graphData.nodes)
        .force('link', d3.forceLink(graphData.links).id(d => d.id).distance(80))
        .force('charge', d3.forceManyBody().strength(-120))
        .force('center', d3.forceCenter(width / 2, height / 2));

    const link = svg.append('g')
        .selectAll('line')
        .data(graphData.links)
        .enter().append('line')
        .attr('class', 'link')
        .style('stroke', '#a855f7')
        .style('stroke-opacity', 0.4);

    const node = svg.append('g')
        .selectAll('.node')
        .data(graphData.nodes)
        .enter().append('g')
        .attr('class', 'node')
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));

    node.append('circle')
        .attr('r', d => d.r)
        .style('fill', d => {
            const colors = ['#9d4edd', '#00b4d8', '#3fb950', '#ffb703', '#f85149', '#9b5de5', '#2f81f7'];
            return colors[d.group - 1] || '#fff';
        })
        .style('stroke', 'rgba(255,255,255,0.2)');

    node.append('text')
        .attr('dx', 14)
        .attr('dy', '.35em')
        .text(d => d.label)
        .style('fill', '#8b949e')
        .style('font-size', '10px')
        .style('pointer-events', 'none');

    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);

        node
            .attr('transform', d => `translate(${d.x},${d.y})`);
    });

    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
}
