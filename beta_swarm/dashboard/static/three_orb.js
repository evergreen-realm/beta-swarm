/**
 * JARVIS 3D Orb Visualization using Three.js
 * Pulses and changes color based on swarm heartbeat.
 */

class SwarmOrb {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(75, this.container.clientWidth / this.container.clientHeight, 0.1, 1000);
        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.container.appendChild(this.renderer.domElement);
        
        this.setupOrb();
        this.setupLights();
        this.camera.position.z = 5;
        
        this.animate();
    }

    setupOrb() {
        const geometry = new THREE.SphereGeometry(2, 64, 64);
        this.material = new THREE.MeshPhongMaterial({
            color: 0x00f2ff,
            wireframe: true,
            transparent: true,
            opacity: 0.5,
            emissive: 0x00f2ff,
            emissiveIntensity: 0.5
        });
        
        this.orb = new THREE.Mesh(geometry, this.material);
        this.scene.add(this.orb);
        
        // Inner core
        const coreGeo = new THREE.IcosahedronGeometry(1, 2);
        const coreMat = new THREE.MeshBasicMaterial({ color: 0x00f2ff });
        this.core = new THREE.Mesh(coreGeo, coreMat);
        this.scene.add(this.core);
    }

    setupLights() {
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
        this.scene.add(ambientLight);
        const pointLight = new THREE.PointLight(0x00f2ff, 1);
        pointLight.position.set(5, 5, 5);
        this.scene.add(pointLight);
    }

    updateStatus(status) {
        // status: healthy, warning, error
        switch(status) {
            case 'healthy':
                this.material.color.setHex(0x00f2ff);
                this.material.emissive.setHex(0x00f2ff);
                break;
            case 'warning':
                this.material.color.setHex(0xff9900);
                this.material.emissive.setHex(0xff9900);
                break;
            case 'error':
                this.material.color.setHex(0xff3333);
                this.material.emissive.setHex(0xff3333);
                break;
        }
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        
        this.orb.rotation.y += 0.005;
        this.orb.rotation.x += 0.002;
        
        const pulse = 1 + Math.sin(Date.now() * 0.002) * 0.05;
        this.orb.scale.set(pulse, pulse, pulse);
        this.core.scale.set(pulse * 0.5, pulse * 0.5, pulse * 0.5);
        
        this.renderer.render(this.scene, this.camera);
    }
}
