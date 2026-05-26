// galaxy.js - Interactive 2D background particle engine

class GalaxyBackground {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        this.particles = [];
        this.maxParticles = 800; // Optimized for performance (T490 safe)
        this.animationId = null;
        
        this.init();
        this.animate();
        
        window.addEventListener('resize', () => this.resize());
    }

    init() {
        this.resize();
        this.particles = [];
        for (let i = 0; i < this.maxParticles; i++) {
            this.particles.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                radius: Math.random() * 1.5 + 0.5,
                color: Math.random() > 0.8 ? 'rgba(157, 78, 221, 0.4)' : 'rgba(255, 255, 255, 0.15)',
                speedX: (Math.random() - 0.5) * 0.2,
                speedY: (Math.random() - 0.5) * 0.2
            });
        }
    }

    resize() {
        if (!this.canvas) return;
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }

    animate() {
        if (!this.ctx) return;
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Draw galaxy central glow
        const grad = this.ctx.createRadialGradient(
            this.canvas.width / 2, this.canvas.height / 2, 10,
            this.canvas.width / 2, this.canvas.height / 2, Math.max(this.canvas.width, this.canvas.height) * 0.6
        );
        grad.addColorStop(0, 'rgba(30, 10, 50, 0.15)');
        grad.addColorStop(0.5, 'rgba(10, 5, 25, 0.05)');
        grad.addColorStop(1, 'rgba(0, 0, 0, 0)');
        
        this.ctx.fillStyle = grad;
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw and update particles
        this.ctx.fillStyle = '#ffffff';
        this.particles.forEach(p => {
            this.ctx.fillStyle = p.color;
            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
            this.ctx.fill();

            // Update position
            p.x += p.speedX;
            p.y += p.speedY;

            // Boundary wrapping
            if (p.x < 0) p.x = this.canvas.width;
            if (p.x > this.canvas.width) p.x = 0;
            if (p.y < 0) p.y = this.canvas.height;
            if (p.y > this.canvas.height) p.y = 0;
        });

        this.animationId = requestAnimationFrame(() => this.animate());
    }

    destroy() {
        if (this.animationId) cancelAnimationFrame(this.animationId);
    }
}

// Instantiate on load
document.addEventListener('DOMContentLoaded', () => {
    window.galaxyBackground = new GalaxyBackground('galaxy-canvas');
});
