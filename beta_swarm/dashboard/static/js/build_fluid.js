// Simple Three.js Fluid Mock for Build Mode Header
(function() {
    const script = document.createElement('script');
    script.src = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js";
    script.onload = initFluid;
    document.head.appendChild(script);

    function initFluid() {
        const container = document.getElementById('fluid-canvas-container');
        if (!container) return;

        const scene = new THREE.Scene();
        scene.background = new THREE.Color('#0d1117');
        
        const camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000);
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        
        renderer.setSize(container.clientWidth, container.clientHeight);
        container.appendChild(renderer.domElement);

        const geometry = new THREE.PlaneGeometry(10, 10, 32, 32);
        const material = new THREE.MeshBasicMaterial({ 
            color: 0x2f81f7, 
            wireframe: true,
            transparent: true,
            opacity: 0.3
        });
        
        const plane = new THREE.Mesh(geometry, material);
        plane.rotation.x = -Math.PI / 3;
        scene.add(plane);
        
        camera.position.z = 3;
        camera.position.y = 1;

        let time = 0;
        function animate() {
            requestAnimationFrame(animate);
            time += 0.01;
            
            const position = plane.geometry.attributes.position;
            for (let i = 0; i < position.count; i++) {
                const vx = position.getX(i);
                const vy = position.getY(i);
                const wave = Math.sin(vx + time) * Math.cos(vy + time) * 0.5;
                position.setZ(i, wave);
            }
            position.needsUpdate = true;
            
            renderer.render(scene, camera);
        }
        
        animate();
        window.fluidInstance = true;

        window.addEventListener('resize', () => {
            if (container.clientWidth) {
                camera.aspect = container.clientWidth / container.clientHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(container.clientWidth, container.clientHeight);
            }
        });
    }
})();
