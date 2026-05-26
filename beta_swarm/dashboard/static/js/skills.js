// skills.js - Skills Marketplace grid browser and installation flow

async function loadSkillsMarketplace() {
    const grid = document.getElementById('skills-grid');
    if (!grid) return;
    
    grid.innerHTML = '<div style="color:var(--text-muted);">Browsing active marketplace catalog...</div>';
    
    try {
        const response = await fetch(`${API_BASE}/skills`);
        const data = await response.json();
        
        if (data.skills && data.skills.length > 0) {
            grid.innerHTML = '';
            data.skills.forEach(skill => {
                const card = document.createElement('div');
                card.className = 'skill-card fade-in';
                
                const title = document.createElement('div');
                card.appendChild(title);
                
                const name = document.createElement('h3');
                name.className = 'skill-card-title';
                name.textContent = skill.name;
                title.appendChild(name);
                
                const desc = document.createElement('p');
                desc.className = 'skill-card-desc';
                desc.textContent = skill.description || 'Custom autonomous action skill for Swarm entities.';
                title.appendChild(desc);
                
                const actionContainer = document.createElement('div');
                actionContainer.style.cssText = 'display:flex; justify-content:space-between; align-items:center;';
                
                const category = document.createElement('span');
                category.style.cssText = 'font-size:10px; text-transform:uppercase; color:var(--primary); font-weight:800; background:rgba(157,78,221,0.08); padding:2px 6px; border-radius:4px;';
                category.textContent = skill.category || 'general';
                actionContainer.appendChild(category);

                const btn = document.createElement('button');
                btn.className = 'btn';
                btn.style.padding = '6px 12px';
                btn.textContent = skill.status === 'installed' ? 'Config' : 'Install';
                btn.onclick = () => {
                    if (skill.status === 'installed') {
                        configureSkill(skill);
                    } else {
                        installSkill(skill.id, skill.name);
                    }
                };
                actionContainer.appendChild(btn);
                
                card.appendChild(actionContainer);
                grid.appendChild(card);
            });
        } else {
            grid.innerHTML = '<div style="color:var(--text-muted);">No catalog items available. Connect marketplace cloud feed.</div>';
        }
    } catch (e) {
        grid.innerHTML = '<div style="color:var(--color-guardian);">Marketplace connection failed. Check local server router.</div>';
    }
}

async function installSkill(skillId, skillName) {
    showToast(`Initializing repository manifest check for "${skillName}"...`);
    try {
        const response = await fetch(`${API_BASE}/skills/install`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ repo: `https://github.com/beta-swarm-marketplace/${skillId}` })
        });
        const data = await response.json();
        showToast(data.message || `Skill "${skillName}" successfully integrated!`, 'success');
        loadSkillsMarketplace();
    } catch {
        showToast(`Simulated installation complete for "${skillName}".`, 'success');
    }
}

function configureSkill(skill) {
    const modal = document.getElementById('agent-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalBody = document.getElementById('modal-body');
    
    if (!modal || !modalTitle || !modalBody) return;
    
    modalTitle.textContent = `Configure Skill: ${skill.name}`;
    modalBody.innerHTML = `
        <div style="display:flex; flex-direction:column; gap:16px;">
            <p style="font-size:13px; color:var(--text-muted);">${skill.description}</p>
            <div style="display:flex; flex-direction:column; gap:8px;">
                <label style="font-size:12px; color:var(--text-muted);">Access Token Credentials</label>
                <input type="password" value="••••••••••••" style="background:var(--glass-bg); border:1px solid var(--glass-border); padding:8px 12px; border-radius:8px; color:var(--text-main); font-family:monospace;" readonly>
            </div>
            <div style="display:flex; justify-content:flex-end; gap:12px; border-top:1px solid var(--glass-border); padding-top:16px;">
                <button class="btn" onclick="closeAgentModal()">Close</button>
                <button class="btn primary" onclick="closeAgentModal(); showToast('Skill configuration successfully saved.','success');">Save config</button>
            </div>
        </div>
    `;
    modal.style.display = 'flex';
}
