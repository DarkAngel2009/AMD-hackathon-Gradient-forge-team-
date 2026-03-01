/* ═══════════════════════════════════════════════════════════════
   Architectural Multiverse Engine — Client-side Application v3
   ═══════════════════════════════════════════════════════════════ */

const API = '';  // same origin

// ── State ──
let architectureResults = [];
let comparisonResult = null;
let radarChartInstance = null;
let lastPayload = null;
let architectureDatasets = {};
let activeToggles = {};

// ── DOM refs ──
const form = document.getElementById('input-form');
const generateBtn = document.getElementById('generateBtn');
const archSection = document.getElementById('arch-section');
const archCards = document.getElementById('arch-cards');
const compSection = document.getElementById('comparison-section');
const rankSection = document.getElementById('ranking-section');
const scaffoldSection = document.getElementById('scaffold-section');
const tensionWarning = document.getElementById('tension-warning');
const llmSection = document.getElementById('llm-section');
const complianceSection = document.getElementById('compliance-section');
const diagramSection = document.getElementById('diagram-section');
const downloadsSection = document.getElementById('downloads-section');

// ── Initialize Mermaid ──
if (typeof mermaid !== 'undefined') {
    mermaid.initialize({
        startOnLoad: false,
        theme: 'dark',
        themeVariables: {
            darkMode: true,
            background: '#0a0e1a',
            primaryColor: '#3b82f6',
            primaryTextColor: '#f1f5f9',
            primaryBorderColor: '#3b82f6',
            lineColor: '#64748b',
            secondaryColor: '#8b5cf6',
            tertiaryColor: '#111827',
        },
    });
}

// ── Slider live-value binding ──
document.querySelectorAll('.priority-slider').forEach(slider => {
    const valSpan = document.getElementById(slider.id + 'Val');
    if (valSpan) {
        slider.addEventListener('input', () => { valSpan.textContent = slider.value; });
    }
});

// ── Model Config ──
document.getElementById('applyModelsBtn')?.addEventListener('click', async () => {
    const config = {
        strategic_analysis: document.getElementById('model-strategic')?.value,
        scaffold: document.getElementById('model-scaffold')?.value,
        compliance: document.getElementById('model-compliance')?.value,
    };
    try {
        await fetch(`${API}/api/models`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config),
        });
        showToast('Model configuration applied ✓');
    } catch (err) {
        showToast('Failed to apply model config', true);
    }
});

// ═══════════════════════════════════════
//  FORM SUBMIT → Generate Architectures
// ═══════════════════════════════════════

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    setLoading(true);

    const payload = {
        system_description: document.getElementById('sysDesc').value.trim(),
        expected_users: parseInt(document.getElementById('expectedUsers').value),
        budget_sensitivity: document.getElementById('budget').value,
        fault_tolerance: 'high',
        time_to_market: document.getElementById('timeToMarket').value,
        cost_weight: parseInt(document.getElementById('costWeight').value),
        scalability_weight: 5,
        speed_weight: parseInt(document.getElementById('speedWeight').value),
        reliability_weight: 5,
    };
    lastPayload = payload;

    try {
        // Step 1: Generate
        const genRes = await fetch(`${API}/api/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (!genRes.ok) throw new Error(await genRes.text());
        architectureResults = await genRes.json();

        // Step 2: Compliance (parallel)
        const compliancePromise = fetch(`${API}/api/compliance`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        }).then(r => r.ok ? r.json() : null).catch(() => null);

        // Step 3: Compare
        const cmpRes = await fetch(`${API}/api/compare`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                results: architectureResults,
                system_input: payload,
            }),
        });
        if (!cmpRes.ok) throw new Error(await cmpRes.text());
        comparisonResult = await cmpRes.json();

        // Wait for compliance
        const complianceData = await compliancePromise;

        // Render everything
        renderCompliancePanel(complianceData);
        renderArchitectureCards(architectureResults);
        renderDiagramButtons(architectureResults);
        renderComparisonTable(architectureResults);
        renderRadarToggles(architectureResults);
        renderRadarChart(architectureResults);
        renderTensionWarning(comparisonResult);
        renderRanking(comparisonResult);
        renderLLMAnalysis(comparisonResult);
        renderScaffoldButtons(architectureResults);

        showSection(complianceSection);
        showSection(archSection);
        showSection(diagramSection);
        showSection(compSection);
        showSection(rankSection);
        showSection(scaffoldSection);
        showSection(downloadsSection);

        archSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (err) {
        alert('Error: ' + err.message);
        console.error(err);
    } finally {
        setLoading(false);
    }
});

// ═══════════════════════════════════════
//  Renderers
// ═══════════════════════════════════════

function renderCompliancePanel(data) {
    if (!data) {
        complianceSection.classList.add('hidden');
        return;
    }

    const badges = document.getElementById('compliance-badges');
    badges.innerHTML = (data.compliance_requirements || []).map(req =>
        `<span class="compliance-badge">${req}</span>`
    ).join('');

    document.getElementById('compliance-implications-text').textContent =
        data.architectural_implications || 'No specific implications detected.';

    const riskList = document.getElementById('compliance-risks-list');
    riskList.innerHTML = (data.risk_flags || []).map(r =>
        `<div class="risk-flag"><span class="risk-icon">⚠</span> ${r}</div>`
    ).join('');
}

function renderArchitectureCards(results) {
    archCards.innerHTML = '';

    // Sort by overall_score descending — best first
    const sorted = [...results].sort((a, b) => b.overall_score - a.overall_score);

    sorted.forEach((r, idx) => {
        const a = r.architecture;
        const card = document.createElement('div');
        card.className = 'arch-card' + (idx === 0 ? ' best-pick' : '');
        card.dataset.style = a.style;

        const bestBadge = idx === 0
            ? '<span class="best-pick-badge">★ Best Pick</span>'
            : `<span class="rank-badge">#${idx + 1}</span>`;

        // Build scoring insight section from breakdown
        const bd = r.scoring_breakdown || {};
        const insightHtml = bd.latency_reasoning ? `
            <details class="scoring-insight">
                <summary class="scoring-insight-toggle">▸ Scoring Insight</summary>
                <div class="scoring-insight-body">
                    ${bd.websocket_assessment ? `<div class="insight-row"><span class="insight-label">WebSocket</span><span class="insight-value">${bd.websocket_assessment}</span></div>` : ''}
                    ${bd.cost_estimate ? `<div class="insight-row"><span class="insight-label">Cost Est.</span><span class="insight-value">${bd.cost_estimate}</span></div>` : ''}
                    ${bd.latency_reasoning ? `<div class="insight-row"><span class="insight-label">Latency</span><span class="insight-value">${bd.latency_reasoning}</span></div>` : ''}
                    ${bd.scalability_reasoning ? `<div class="insight-row"><span class="insight-label">Scale</span><span class="insight-value">${bd.scalability_reasoning}</span></div>` : ''}
                    ${bd.resilience_reasoning ? `<div class="insight-row"><span class="insight-label">Resilience</span><span class="insight-value">${bd.resilience_reasoning}</span></div>` : ''}
                    ${bd.cost_reasoning ? `<div class="insight-row"><span class="insight-label">Cost</span><span class="insight-value">${bd.cost_reasoning}</span></div>` : ''}
                </div>
            </details>
        ` : '';

        card.innerHTML = `
            ${bestBadge}
            <h3>${a.name}</h3>
            <p class="desc">${a.description}</p>

            ${insightHtml}

            <div class="diagram-box">
                <div class="arch-detail-label">Component Diagram</div>
                <div class="diagram-nodes">
                    ${a.component_diagram.nodes.map(n => `<span class="diagram-node">${n}</span>`).join('')}
                </div>
                <div class="diagram-edges">
                    ${a.component_diagram.edges.map(e =>
            `<span class="diagram-edge">${e.from} <span class="arrow">→</span> ${e.to} <em>(${e.label})</em></span>`
        ).join('')}
                </div>
            </div>

            <div class="arch-detail">
                <div class="arch-detail-label">Database Strategy</div>
                <div class="arch-detail-value">${a.database_strategy}</div>
            </div>
            <div class="arch-detail">
                <div class="arch-detail-label">Communication Model</div>
                <div class="arch-detail-value">${a.communication_model}</div>
            </div>
            <div class="arch-detail">
                <div class="arch-detail-label">Scaling Model</div>
                <div class="arch-detail-value">${a.scaling_model}</div>
            </div>
            <div class="arch-detail">
                <div class="arch-detail-label">Failure Domain Analysis</div>
                <div class="arch-detail-value">${a.failure_domain_analysis}</div>
            </div>

            <div class="card-actions">
                <button class="btn-try-now" data-arch="${a.name}">
                    🚀 Try This Architecture
                </button>
            </div>
        `;
        archCards.appendChild(card);
    });

    // Bind Try Now buttons
    document.querySelectorAll('.btn-try-now').forEach(btn => {
        btn.addEventListener('click', () => downloadScaffoldZip(btn.dataset.arch));
    });
}

function renderComparisonTable(results) {
    const thead = document.querySelector('#comparison-table thead');
    const tbody = document.querySelector('#comparison-table tbody');

    thead.innerHTML = `<tr>
        <th>Metric</th>
        ${results.map(r => `<th>${r.architecture.name}</th>`).join('')}
    </tr>`;

    const metrics = [
        { key: 'latency', label: 'Latency (↑ faster)', invert: false },
        { key: 'scalability', label: 'Scalability (↑ better)', invert: false },
        { key: 'operational_complexity', label: 'Op. Complexity (↓ better)', invert: true },
        { key: 'infrastructure_cost', label: 'Infra Cost (↓ better)', invert: true },
        { key: 'resilience', label: 'Resilience (↑ better)', invert: false },
    ];

    const overallRow = `<tr style="border-top:2px solid rgba(255,255,255,0.1);font-weight:700;">
        <td>Overall Score</td>
        ${results.map(r => `<td class="${scoreClass(r.overall_score, false)}">${r.overall_score}</td>`).join('')}
    </tr>`;

    tbody.innerHTML = metrics.map(m => `<tr>
        <td>${m.label}</td>
        ${results.map(r => {
        const val = r.scores[m.key];
        return `<td class="${scoreClass(val, m.invert)}">${val}</td>`;
    }).join('')}
    </tr>`).join('') + overallRow;
}

function scoreClass(val, invert) {
    const effective = invert ? (100 - val) : val;
    if (effective >= 65) return 'score-high';
    if (effective >= 40) return 'score-mid';
    return 'score-low';
}

// ═══════════════════════════════════════
//  Radar Chart with Toggles
// ═══════════════════════════════════════

const ARCH_COLORS = {
    monolith: { bg: 'rgba(59,130,246,0.15)', border: '#3b82f6', label: 'Monolith' },
    microservices: { bg: 'rgba(139,92,246,0.15)', border: '#8b5cf6', label: 'Microservices' },
    event_driven: { bg: 'rgba(16,185,129,0.15)', border: '#10b981', label: 'Event-Driven' },
    serverless: { bg: 'rgba(6,182,212,0.15)', border: '#06b6d4', label: 'Serverless' },
};

function renderRadarToggles(results) {
    const container = document.getElementById('radar-toggles');
    container.innerHTML = '';
    activeToggles = {};
    architectureDatasets = {};

    results.forEach(r => {
        const style = r.architecture.style;
        const c = ARCH_COLORS[style] || ARCH_COLORS.monolith;
        activeToggles[style] = true;

        architectureDatasets[style] = {
            label: r.architecture.name,
            data: [
                r.scores.latency,
                r.scores.scalability,
                100 - r.scores.operational_complexity,
                100 - r.scores.infrastructure_cost,
                r.scores.resilience,
            ],
            backgroundColor: c.bg,
            borderColor: c.border,
            borderWidth: 2,
            pointBackgroundColor: c.border,
            pointRadius: 3,
        };

        const toggle = document.createElement('button');
        toggle.className = 'radar-toggle active';
        toggle.dataset.style = style;
        toggle.style.setProperty('--toggle-color', c.border);
        toggle.innerHTML = `<span class="toggle-dot" style="background:${c.border}"></span> ${r.architecture.name}`;
        toggle.addEventListener('click', () => toggleArchitecture(style, toggle));
        container.appendChild(toggle);
    });
}

function toggleArchitecture(style, btn) {
    activeToggles[style] = !activeToggles[style];
    btn.classList.toggle('active', activeToggles[style]);
    updateRadarChart();
}

function updateRadarChart() {
    if (!radarChartInstance) return;

    const activeStyles = Object.keys(activeToggles).filter(s => activeToggles[s]);
    const datasets = activeStyles.map(style => {
        const ds = { ...architectureDatasets[style] };
        // Focused mode: thicker border for single selection
        if (activeStyles.length === 1) {
            ds.borderWidth = 4;
            ds.pointRadius = 5;
            ds.backgroundColor = ds.backgroundColor.replace('0.15', '0.25');
        } else {
            ds.borderWidth = 2;
            ds.pointRadius = 3;
        }
        return ds;
    });

    radarChartInstance.data.datasets = datasets;

    // Adjust scale for focused view
    if (activeStyles.length === 1 && datasets[0]) {
        const minVal = Math.min(...datasets[0].data);
        radarChartInstance.options.scales.r.min = Math.max(0, Math.floor(minVal / 10) * 10 - 10);
    } else {
        radarChartInstance.options.scales.r.min = 0;
    }

    radarChartInstance.update('active');

    // Show/hide focused badge
    const badge = document.getElementById('focused-view-badge');
    if (activeStyles.length === 1) {
        badge.classList.remove('hidden');
    } else {
        badge.classList.add('hidden');
    }
}

function renderRadarChart(results) {
    const ctx = document.getElementById('radarChart').getContext('2d');

    if (radarChartInstance) radarChartInstance.destroy();

    const activeStyles = Object.keys(activeToggles).filter(s => activeToggles[s]);
    const datasets = activeStyles.map(style => ({ ...architectureDatasets[style] }));

    radarChartInstance = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['Latency', 'Scalability', 'Low Complexity', 'Low Cost', 'Resilience'],
            datasets: datasets,
        },
        options: {
            responsive: true,
            animation: {
                duration: 600,
                easing: 'easeInOutQuart',
            },
            scales: {
                r: {
                    beginAtZero: true,
                    min: 0,
                    max: 100,
                    ticks: { stepSize: 20, color: '#64748b', backdropColor: 'transparent', font: { size: 10 } },
                    grid: { color: 'rgba(255,255,255,0.06)' },
                    angleLines: { color: 'rgba(255,255,255,0.06)' },
                    pointLabels: { color: '#94a3b8', font: { size: 12, weight: '500' } },
                },
            },
            plugins: {
                legend: {
                    labels: { color: '#94a3b8', font: { size: 12 }, usePointStyle: true, padding: 16 },
                },
            },
        },
    });
}

function renderTensionWarning(cmp) {
    if (cmp.constraint_tension_warning) {
        tensionWarning.textContent = cmp.constraint_tension_warning;
        tensionWarning.classList.remove('hidden');
    } else {
        tensionWarning.classList.add('hidden');
    }
}

function renderRanking(cmp) {
    document.getElementById('recommendation').innerHTML = formatMarkdownBold(cmp.recommendation);

    const container = document.getElementById('trade-offs');
    container.innerHTML = cmp.trade_off_reasoning.map(text =>
        `<div class="trade-off-item">${formatMarkdownBold(text)}</div>`
    ).join('');
}

function renderLLMAnalysis(cmp) {
    const analysis = cmp.llm_analysis;
    if (!analysis) {
        llmSection.classList.add('hidden');
        return;
    }

    const formatSection = (text) => {
        if (!text) return '';
        // Convert markdown bold and add paragraph breaks
        return text.split('\n').filter(l => l.trim()).map(l =>
            `<p>${formatMarkdownBold(l)}</p>`
        ).join('');
    };

    document.querySelector('#llm-summary .llm-card-body').innerHTML =
        formatSection(analysis.executive_summary) || '<p>No summary available.</p>';
    document.querySelector('#llm-risk .llm-card-body').innerHTML =
        formatSection(analysis.risk_analysis) || '<p>No risk analysis available.</p>';
    document.querySelector('#llm-advice .llm-card-body').innerHTML =
        formatSection(analysis.strategic_advice) || '<p>No strategic advice available.</p>';

    showSection(llmSection);
}

function renderScaffoldButtons(results) {
    // Store the best architecture name for Get Code
    const sorted = [...results].sort((a, b) => b.overall_score - a.overall_score);
    window._bestArchName = sorted[0]?.architecture?.name || null;

    // Update CTA to show best architecture name
    const ctaText = document.querySelector('.scaffold-cta-text');
    if (ctaText && window._bestArchName) {
        ctaText.textContent = `Generate a working prototype for ${window._bestArchName}?`;
    }

    // Reset scaffold CTA state
    const cta = document.getElementById('scaffold-cta');
    const output = document.getElementById('scaffold-output');
    if (cta) cta.classList.remove('hidden');
    if (output) output.classList.add('hidden');
}

// "Get Code" button — directly generates scaffold for best architecture
document.getElementById('getCodeBtn')?.addEventListener('click', async () => {
    const archName = window._bestArchName;
    if (!archName) return;

    const btn = document.getElementById('getCodeBtn');
    const btnText = btn.querySelector('.btn-text');
    const btnLoader = btn.querySelector('.btn-loader');
    btn.disabled = true;
    btnText.textContent = `Generating ${archName} scaffold...`;
    btnLoader.classList.remove('hidden');

    try {
        await generateScaffold(archName);
        const cta = document.getElementById('scaffold-cta');
        if (cta) cta.classList.add('hidden');
    } catch (err) {
        alert('Scaffold error: ' + err.message);
    } finally {
        btn.disabled = false;
        btnText.textContent = '⟨/⟩   Get Code';
        btnLoader.classList.add('hidden');
    }
});

// ═══════════════════════════════════════
//  Diagram Generation (Mermaid)
// ═══════════════════════════════════════

function renderDiagramButtons(results) {
    const row = document.getElementById('diagram-buttons');
    row.innerHTML = '';

    results.forEach(r => {
        const btn = document.createElement('button');
        btn.className = 'btn-secondary';
        btn.textContent = r.architecture.name;
        btn.addEventListener('click', () => generateDiagram(r));
        row.appendChild(btn);
    });
}

let diagramCounter = 0;

async function generateDiagram(archResult) {
    const container = document.getElementById('diagram-container');
    const output = document.getElementById('mermaid-output');
    const label = document.getElementById('diagram-focused-label');
    const downloadBtn = document.getElementById('downloadDiagramBtn');

    // Highlight active button
    document.querySelectorAll('#diagram-buttons .btn-secondary').forEach(b =>
        b.classList.toggle('active', b.textContent === archResult.architecture.name)
    );

    label.textContent = `📐 ${archResult.architecture.name} Architecture`;

    try {
        const res = await fetch(`${API}/api/diagram`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ architecture: archResult.architecture }),
        });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();

        // Render Mermaid with safety
        diagramCounter++;
        const diagramId = `mermaid-diagram-${diagramCounter}`;
        output.innerHTML = '';

        if (typeof mermaid !== 'undefined') {
            try {
                const { svg } = await mermaid.render(diagramId, data.mermaid);
                output.innerHTML = svg;
            } catch (renderErr) {
                console.warn('Mermaid render failed, showing raw code:', renderErr);
                output.innerHTML = `
                    <div class="diagram-fallback-msg">
                        <p>⚠ Diagram rendering failed. Using simplified structure.</p>
                    </div>
                    <pre class="mermaid-fallback">${escapeHtml(data.mermaid)}</pre>`;
            }
        } else {
            output.innerHTML = `<pre class="mermaid-fallback">${escapeHtml(data.mermaid)}</pre>`;
        }

        container.classList.remove('hidden');
        downloadBtn.classList.remove('hidden');

        // PNG download handler
        downloadBtn.onclick = () => downloadDiagramPng(archResult.architecture.name);
    } catch (err) {
        console.error('Diagram error:', err);
        output.innerHTML = `<p class="error-text">Failed to generate diagram: ${err.message}</p>`;
        container.classList.remove('hidden');
    }
}

function downloadDiagramPng(archName) {
    const svgEl = document.querySelector('#mermaid-output svg');
    if (!svgEl) return;

    const svgData = new XMLSerializer().serializeToString(svgEl);
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const img = new Image();

    img.onload = () => {
        canvas.width = img.width * 2;
        canvas.height = img.height * 2;
        ctx.scale(2, 2);
        ctx.fillStyle = '#0a0e1a';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0);
        canvas.toBlob(blob => {
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `${archName.toLowerCase().replace(/\s+/g, '_')}_diagram.png`;
            a.click();
            URL.revokeObjectURL(a.href);
        }, 'image/png');
    };

    img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgData)));
}

// ═══════════════════════════════════════
//  Scaffold Generation
// ═══════════════════════════════════════

async function generateScaffold(archName) {
    const desc = document.getElementById('sysDesc').value.trim();
    const btns = document.querySelectorAll('.scaffold-btn-row .btn-secondary');
    btns.forEach(b => b.classList.toggle('active', b.textContent === archName));

    try {
        const res = await fetch(`${API}/api/scaffold`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ architecture_name: archName, system_description: desc }),
        });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        renderScaffoldFiles(data.files);
    } catch (err) {
        alert('Scaffold error: ' + err.message);
    }
}

function renderScaffoldFiles(files) {
    const container = document.getElementById('scaffold-files');
    container.innerHTML = '';

    Object.entries(files).forEach(([name, content]) => {
        const div = document.createElement('div');
        div.className = 'scaffold-file';
        div.innerHTML = `
            <div class="scaffold-file-header">📄 ${name}</div>
            <pre>${escapeHtml(content)}</pre>
        `;
        container.appendChild(div);
    });

    document.getElementById('scaffold-output').classList.remove('hidden');
}

// ═══════════════════════════════════════
//  Try Now — Zip Download
// ═══════════════════════════════════════

async function downloadScaffoldZip(archName) {
    const desc = document.getElementById('sysDesc').value.trim();
    const btn = document.querySelector(`.btn-try-now[data-arch="${archName}"]`);
    if (btn) {
        btn.disabled = true;
        btn.textContent = '⏳ Generating...';
    }

    try {
        const res = await fetch(`${API}/api/scaffold/download`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ architecture_name: archName, system_description: desc }),
        });
        if (!res.ok) throw new Error(await res.text());

        const blob = await res.blob();
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `${archName.toLowerCase().replace(/\s+/g, '_')}_scaffold.zip`;
        a.click();
        URL.revokeObjectURL(a.href);
        showToast(`${archName} scaffold downloaded ✓`);
    } catch (err) {
        alert('Download error: ' + err.message);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = '🚀 Try This Architecture';
        }
    }
}

let lastSrsText = '';

document.getElementById('generateSrsBtn')?.addEventListener('click', async () => {
    const btn = document.getElementById('generateSrsBtn');
    const btnText = btn.querySelector('.btn-text');
    const btnLoader = btn.querySelector('.btn-loader');
    const srsContainer = document.getElementById('srs-container');
    const downloadSrsBtn = document.getElementById('downloadSrsBtn');
    btn.disabled = true;
    btnText.textContent = 'Generating...';
    btnLoader.classList.remove('hidden');

    try {
        const res = await fetch(`${API}/api/srs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                system_input: lastPayload,
                architecture_results: architectureResults,
                comparison_result: comparisonResult,
            }),
        });
        if (!res.ok) throw new Error(await res.text());

        lastSrsText = await res.text();

        // Render markdown in-page
        try {
            if (typeof marked !== 'undefined') {
                srsContainer.innerHTML = marked.parse(lastSrsText);
            } else {
                srsContainer.innerHTML = `<pre>${escapeHtml(lastSrsText)}</pre>`;
            }
        } catch (parseErr) {
            console.warn('Markdown parsing failed, showing raw text:', parseErr);
            srsContainer.innerHTML = `<pre>${escapeHtml(lastSrsText)}</pre>`;
        }

        srsContainer.classList.remove('hidden');
        downloadSrsBtn.classList.remove('hidden');
        showToast('SRS document generated ✓');
    } catch (err) {
        alert('SRS error: ' + err.message);
    } finally {
        btn.disabled = false;
        btnText.textContent = 'Generate SRS';
        btnLoader.classList.add('hidden');
    }
});

// SRS download handler
document.getElementById('downloadSrsBtn')?.addEventListener('click', () => {
    if (!lastSrsText) return;
    const blob = new Blob([lastSrsText], { type: 'text/markdown' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'srs_document.md';
    a.click();
    URL.revokeObjectURL(a.href);
    showToast('SRS document downloaded ✓');
});

// ═══════════════════════════════════════
//  Helpers
// ═══════════════════════════════════════

function setLoading(loading) {
    generateBtn.disabled = loading;
    generateBtn.querySelector('.btn-text').classList.toggle('hidden', loading);
    generateBtn.querySelector('.btn-loader').classList.toggle('hidden', !loading);
}

function showSection(el) { el.classList.remove('hidden'); }

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatMarkdownBold(text) {
    return text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
}

// ── Toast Notification ──
function showToast(msg, isError = false) {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast ${isError ? 'toast-error' : 'toast-success'}`;
    toast.textContent = msg;
    document.body.appendChild(toast);

    requestAnimationFrame(() => toast.classList.add('toast-visible'));
    setTimeout(() => {
        toast.classList.remove('toast-visible');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
