// Beta Swarm Portfolio — app.js

// Smooth reveal on scroll
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.style.opacity = '1';
      entry.target.style.transform = 'translateY(0)';
    }
  });
}, { threshold: 0.15 });

document.querySelectorAll('section:not(#hero)').forEach(section => {
  section.style.opacity = '0';
  section.style.transform = 'translateY(24px)';
  section.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
  observer.observe(section);
});

// Contact form handler
const form = document.getElementById('contact-form');
const statusEl = document.getElementById('form-status');

if (form) {
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('name').value.trim();
    const email = document.getElementById('email').value.trim();
    const message = document.getElementById('message').value.trim();

    if (!name || !email || !message) {
      statusEl.textContent = 'Please fill in all fields.';
      statusEl.className = 'form-status error';
      return;
    }

    // Simulate async submission
    statusEl.textContent = 'Sending...';
    statusEl.className = 'form-status';
    await new Promise(r => setTimeout(r, 800));
    statusEl.textContent = `Thanks ${name}! Your message was received.`;
    statusEl.className = 'form-status success';
    form.reset();
  });
}

console.log('[Beta Swarm] Portfolio loaded — real-test-portfolio-001');
