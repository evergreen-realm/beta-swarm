import webview
import threading
import sys
import os

# Galaxy HTML with Three.js
galaxy_html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* { margin: 0; padding: 0; overflow: hidden; background: #000; }
body { font-family: -apple-system, sans-serif; }
#canvas-container { width: 100vw; height: 100vh; position: fixed; top: 0; left: 0; }
.hud {
  position: fixed; top: 0; left: 0; right: 0;
  padding: 16px 24px;
  display: flex; justify-content: space-between; align-items: center;
  background: linear-gradient(to bottom, rgba(0,0,0,0.8), transparent);
  color: #e6edf3; font-size: 13px; pointer-events: none;
}
.hud-left { font-weight: 600; letter-spacing: 0.05em; }
.hud-right { display: flex; gap: 24px; color: #8b949e; }
.hud-right span { display: flex; align-items: center; gap: 6px; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: #3fb950; }
.agent-panel {
  position: fixed; bottom: 0; left: 0; right: 0;
  height: 0; background: rgba(13,17,23,0.95);
  border-top: 1px solid #30363d;
  transition: height 0.3s ease;
  padding: 0 24px;
  overflow-y: auto;
}
.agent-panel.open { height: 280px; padding: 24px; }
.agent-panel h3 { color: #e6edf3; margin-bottom: 12px; }
.agent-panel pre {
  background: #161b22; padding: 12px; border-radius: 8px;
  color: #8b949e; font-family: monospace; font-size: 12px;
  overflow-x: auto;
}
.voice-indicator {
  position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
  background: rgba(13,17,23,0.9); padding: 8px 16px; border-radius: 20px;
  border: 1px solid #30363d; color: #8b949e; font-size: 12px;
  display: flex; align-items: center; gap: 8px;
}
.voice-pulse {
  width: 8px; height: 8px; border-radius: 50%;
  background: #2f81f7; animation: pulse 1.5s infinite;
}
@keyframes pulse { 0%,100% { opacity: 0.4; } 50% { opacity: 1; } }
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
</head>
<body>
<div id="canvas-container"></div>
<div class="hud">
  <div class="hud-left">BETA SWARM // ENTITY GALAXY</div>
  <div class="hud-right">
    <span><div class="status-dot"></div> ONLINE</span>
    <span id="agent-count">Agents: 36</span>
    <span id="node-count">Nodes: 1</span>
    <span id="project-count">Projects: 0</span>
  </div>
</div>
<div class="agent-panel" id="agent-panel">
  <h3 id="panel-title">Select an agent</h3>
  <div id="panel-content">Click any orb to view details</div>
</div>
<div class="voice-indicator">
  <div class="voice-pulse"></div>
  Say "Open Dashboard" or "Show Status"
</div>

<script>
// Three.js Galaxy
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth/window.innerHeight, 0.1, 2000);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
document.getElementById('canvas-container').appendChild(renderer.domElement);

// Galaxy parameters
const params = {
  count: 8000,
  size: 0.05,
  radius: 5,
  branches: 3,
  spin: 1,
  randomness: 0.2,
  randomnessPower: 3,
  insideColor: '#2f81f7',
  outsideColor: '#a020f0'
};

// Generate galaxy
const geometry = new THREE.BufferGeometry();
const positions = new Float32Array(params.count * 3);
const colors = new Float32Array(params.count * 3);
const colorInside = new THREE.Color(params.insideColor);
const colorOutside = new THREE.Color(params.outsideColor);

for(let i = 0; i < params.count; i++) {
  const i3 = i * 3;
  const radius = Math.random() * params.radius;
  const spinAngle = radius * params.spin;
  const branchAngle = (i % params.branches) / params.branches * Math.PI * 2;
  const randomX = Math.pow(Math.random(), params.randomnessPower) * (Math.random() < 0.5 ? 1 : -1);
  const randomY = Math.pow(Math.random(), params.randomnessPower) * (Math.random() < 0.5 ? 1 : -1);
  const randomZ = Math.pow(Math.random(), params.randomnessPower) * (Math.random() < 0.5 ? 1 : -1);

  positions[i3] = Math.cos(branchAngle + spinAngle) * radius + randomX;
  positions[i3 + 1] = randomY;
  positions[i3 + 2] = Math.sin(branchAngle + spinAngle) * radius + randomZ;

  const mixedColor = colorInside.clone().lerp(colorOutside, radius / params.radius);
  colors[i3] = mixedColor.r;
  colors[i3 + 1] = mixedColor.g;
  colors[i3 + 2] = mixedColor.b;
}

geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

const material = new THREE.PointsMaterial({
  size: params.size,
  sizeAttenuation: true,
  depthWrite: false,
  blending: THREE.AdditiveBlending,
  vertexColors: true
});

const galaxy = new THREE.Points(geometry, material);
scene.add(galaxy);

// Agent orbs
const agents = [
  {id: 's1', name: 'Ideation', stage: 'S1', angle: 0, radius: 2, color: 0x2f81f7},
  {id: 's2', name: 'Research', stage: 'S2', angle: 0.5, radius: 2.3, color: 0x388bfd},
  {id: 's3', name: 'PRD', stage: 'S3', angle: 1.0, radius: 2.6, color: 0x58a6ff},
  {id: 's4', name: 'Architecture', stage: 'S4', angle: 1.5, radius: 2.9, color: 0x79c0ff},
  {id: 's5', name: 'Backend', stage: 'S5', angle: 2.0, radius: 3.2, color: 0x6366f1},
  {id: 's6', name: 'API', stage: 'S6', angle: 2.5, radius: 3.5, color: 0x8b5cf6},
  {id: 's7', name: 'Frontend', stage: 'S7', angle: 3.0, radius: 3.8, color: 0xa855f7},
  {id: 's8', name: 'Testing', stage: 'S8', angle: 3.5, radius: 4.1, color: 0xd946ef},
  {id: 's9', name: 'Deployment', stage: 'S9', angle: 4.0, radius: 4.4, color: 0x10b981},
  {id: 's10', name: 'Monitoring', stage: 'S10', angle: 4.5, radius: 2.1, color: 0x34d399},
  {id: 's11', name: 'Docs', stage: 'S11', angle: 5.0, radius: 2.4, color: 0x6ee7b7},
  {id: 's12', name: 'Maintenance', stage: 'S12', angle: 5.5, radius: 2.7, color: 0xf59e0b},
  {id: 's13', name: 'Design', stage: 'S13', angle: 6.0, radius: 3.0, color: 0xfbbf24},
  {id: 'b1', name: 'Brain', stage: 'CORE', angle: 0, radius: 0, color: 0xffffff},
  {id: 'b3', name: 'Growth', stage: 'GROWTH', angle: 1.5, radius: 0.8, color: 0xff6b6b},
  {id: 'r1', name: 'Review', stage: 'REVIEW', angle: 3.0, radius: 0.8, color: 0xfeca57},
  {id: 'se1', name: 'Sentry', stage: 'SENTRY', angle: 4.5, radius: 0.8, color: 0x48dbfb},
];

const agentMeshes = [];
agents.forEach(agent => {
  const geom = new THREE.SphereGeometry(0.15, 16, 16);
  const mat = new THREE.MeshBasicMaterial({ 
    color: agent.color,
    transparent: true,
    opacity: 0.9
  });
  const mesh = new THREE.Mesh(geom, mat);
  
  if (agent.radius === 0) {
    mesh.position.set(0, 0, 0);
  } else {
    mesh.position.set(
      Math.cos(agent.angle) * agent.radius,
      0,
      Math.sin(agent.angle) * agent.radius
    );
  }
  
  mesh.userData = agent;
  scene.add(mesh);
  agentMeshes.push(mesh);
  
  // Glow ring
  const ringGeom = new THREE.RingGeometry(0.2, 0.25, 32);
  const ringMat = new THREE.MeshBasicMaterial({ 
    color: agent.color, 
    transparent: true, 
    opacity: 0.3,
    side: THREE.DoubleSide
  });
  const ring = new THREE.Mesh(ringGeom, ringMat);
  ring.position.copy(mesh.position);
  ring.rotation.x = Math.PI / 2;
  scene.add(ring);
});

camera.position.set(0, 5, 8);
camera.lookAt(0, 0, 0);

// Raycaster for clicks
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();

window.addEventListener('click', (event) => {
  mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
  mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
  raycaster.setFromCamera(mouse, camera);
  const intersects = raycaster.intersectObjects(agentMeshes);
  if (intersects.length > 0) {
    const agent = intersects[0].object.userData;
    showAgentPanel(agent);
  }
});

function showAgentPanel(agent) {
  const panel = document.getElementById('agent-panel');
  document.getElementById('panel-title').textContent = `${agent.name} (${agent.id.toUpperCase()})`;
  document.getElementById('panel-content').innerHTML = `
    <p><strong>Stage:</strong> ${agent.stage}</p>
    <p><strong>Status:</strong> Idle</p>
    <pre>// Agent output will appear here
// Click "Open Dashboard" for full details</pre>
    <div style="margin-top: 12px;">
      <button onclick="openDashboard()" style="background: #2f81f7; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer;">Open Dashboard</button>
      <button onclick="openVSCode()" style="background: #21262d; color: #e6edf3; border: 1px solid #30363d; padding: 8px 16px; border-radius: 6px; cursor: pointer; margin-left: 8px;">Open in VS Code</button>
    </div>
  `;
  panel.classList.add('open');
}

function openDashboard() {
  if (window.pywebview) {
    window.pywebview.api.open_dashboard();
  }
}

function openVSCode() {
  window.location.href = 'vscode://file/C:/Users/Admin/Documents/Beta%20Swarnv2';
}

// Animation
const clock = new THREE.Clock();
function animate() {
  requestAnimationFrame(animate);
  const elapsed = clock.getElapsedTime();
  
  galaxy.rotation.y = elapsed * 0.05;
  
  // Orbit agents
  agentMeshes.forEach((mesh, i) => {
    const agent = agents[i];
    if (agent.radius > 0) {
      const speed = 0.1 + (i * 0.02);
      mesh.position.x = Math.cos(agent.angle + elapsed * speed) * agent.radius;
      mesh.position.z = Math.sin(agent.angle + elapsed * speed) * agent.radius;
      // Update ring position
      scene.children.find(c => c.geometry && c.geometry.type === 'RingGeometry' && c.position.distanceTo(mesh.position) < 0.1)?.position.copy(mesh.position);
    }
    // Pulse effect
    mesh.material.opacity = 0.7 + Math.sin(elapsed * 2 + i) * 0.2;
  });
  
  renderer.render(scene, camera);
}
animate();

// Resize
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
</script>
</body>
</html>
"""

class GalaxyAPI:
    def open_dashboard(self):
        import subprocess
        subprocess.Popen([
            sys.executable, "-m", "beta_swarm.entity.native_window"
        ], cwd=r"C:\Users\Admin\Documents\Beta Swarnv2")

def launch_galaxy_window():
    window = webview.create_window(
        "Beta Swarm // Galaxy",
        html=galaxy_html,
        width=1440,
        height=900,
        min_size=(900, 600),
        resizable=True,
        fullscreen=False
    )
    window.expose(GalaxyAPI().open_dashboard)
    webview.start(debug=False)

if __name__ == "__main__":
    launch_galaxy_window()
