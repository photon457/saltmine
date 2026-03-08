const brandInput = document.getElementById("brandInput");
const searchBtn = document.getElementById("searchBtn");
const statusArea = document.getElementById("statusArea");
const resultArea = document.getElementById("resultArea");
const prescribedMeta = document.getElementById("prescribedMeta");
const compositionList = document.getElementById("compositionList");
const alternativesBody = document.getElementById("alternativesBody");

// Initialize on Enter key in input
brandInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !searchBtn.disabled) {
        searchBrand();
    }
});

searchBtn.addEventListener("click", searchBrand);

async function searchBrand() {
    const brand = brandInput.value.trim();
    
    if (!brand) {
        setStatus("Please enter a brand name to search.", true);
        return;
    }

    if (brand.length < 2) {
        setStatus("Brand name must be at least 2 characters.", true);
        return;
    }

    // Disable button and show loading state
    searchBtn.disabled = true;
    searchBtn.textContent = "Searching...";
    setStatus("Searching medicine database...", false);
    resultArea.classList.add("hidden");

    try {
        const res = await fetch(`/api/search?brand=${encodeURIComponent(brand)}`);
        const data = await res.json();

        if (!res.ok) {
            setStatus(`❌ ${data.error || "Unable to fetch results."}`, true);
            searchBtn.disabled = false;
            searchBtn.textContent = "Search";
            return;
        }

        renderResults(data);
        setStatus(`✅ Results loaded via ${data.backend_used === 'sql' ? 'Primary SQL' : 'Fallback TXT'} backend.`, false);
        
        // Scroll to results
        setTimeout(() => {
            resultArea.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 300);
        
    } catch (err) {
        console.error('Search error:', err);
        setStatus("❌ Network error while searching. Please check your connection.", true);
    } finally {
        searchBtn.disabled = false;
        searchBtn.textContent = "Search";
    }
}

function setStatus(message, isError) {
    statusArea.textContent = message;
    statusArea.className = `status ${isError ? "error" : "ok"}`;
    statusArea.setAttribute("aria-live", "polite");
}

function renderResults(data) {
    const p = data.prescribed;
    
    // Render prescribed medicine
    prescribedMeta.innerHTML = `
        <div style="border-radius: 8px; background: #f0f4ff; padding: 1rem; margin-bottom: 1rem;">
            <p style="margin: 0 0 0.5rem 0;"><strong style="font-size: 1.15rem; color: var(--primary);">${escapeHtml(p.brand_name)}</strong></p>
            <p style="margin: 0.3rem 0; color: var(--text-secondary);"><strong>Manufacturer:</strong> ${escapeHtml(p.manufacturer)}</p>
            <p style="margin: 0.3rem 0; color: var(--text-primary);"><strong>Price:</strong> <span style="font-size: 1.2rem; color: var(--primary);">₹${Number(p.price_inr).toFixed(2)}</span></p>
            <p style="margin: 0.3rem 0; font-size: 0.9rem; color: var(--text-secondary);">
                <strong>Status:</strong> ${Number(p.is_jan_aushadhi) === 1 ? '🟢 Jan Aushadhi (Generic)' : '🔵 Branded'}
            </p>
        </div>
    `;

    // Render composition
    compositionList.innerHTML = "";
    if (data.composition.length === 0) {
        compositionList.innerHTML = '<li style="color: var(--text-secondary);">No composition data available</li>';
    } else {
        data.composition.forEach((item, index) => {
            const li = document.createElement("li");
            li.innerHTML = `
                <strong>${escapeHtml(item.salt_name)}</strong> 
                <span style="color: var(--text-secondary); margin-left: 0.5rem;">— ${Number(item.strength_mg)} mg</span>
            `;
            compositionList.appendChild(li);
        });
    }

    // Render alternatives table
    alternativesBody.innerHTML = "";
    
    if (!data.alternatives || data.alternatives.length === 0) {
        alternativesBody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; padding: 2rem; color: var(--text-secondary); font-size: 0.95rem;">
                    No chemically identical alternatives found in the database.
                </td>
            </tr>
        `;
    } else {
        data.alternatives.forEach((alt, index) => {
            const row = document.createElement("tr");
            const isJA = Number(alt.is_jan_aushadhi) === 1;
            const savings = Number(alt.savings_pct || 0);
            const isCheaper = savings > 0;
            
            row.style.animation = `slideUp 0.5s ease-out ${index * 0.05}s backwards`;
            
            row.innerHTML = `
                <td>
                    <strong style="color: ${isCheaper && isJA ? 'var(--success)' : 'var(--text-primary)'};">
                        ${escapeHtml(alt.brand_name)}
                    </strong>
                </td>
                <td>
                    <span style="font-size: 0.9rem; color: var(--text-secondary);">
                        ${escapeHtml(alt.manufacturer)}
                    </span>
                </td>
                <td>
                    <strong>${Number(alt.price_inr).toFixed(2)}</strong>
                </td>
                <td>
                    <span style="color: ${isCheaper ? 'var(--success)' : 'var(--text-secondary)'}; font-weight: 600;">
                        ${isCheaper ? '✓ ' : ''}${savings.toFixed(2)}%
                    </span>
                </td>
                <td>
                    <span class="tag ${isJA ? 'ja' : 'brand'}">
                        ${isJA ? '🟢 Jan Aushadhi' : '🔵 Branded'}
                    </span>
                </td>
            `;
            alternativesBody.appendChild(row);
        });
    }

    resultArea.classList.remove("hidden");
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// ── Autocomplete / Suggestions ──
let suggestTimer = null;
const suggestBox = document.getElementById("suggestBox");

brandInput.addEventListener("input", () => {
    clearTimeout(suggestTimer);
    const q = brandInput.value.trim();
    if (q.length < 2) {
        hideSuggestions();
        return;
    }
    suggestTimer = setTimeout(() => fetchSuggestions(q), 250);
});

document.addEventListener("click", (e) => {
    if (!e.target.closest(".search-card")) hideSuggestions();
});

async function fetchSuggestions(q) {
    try {
        const res = await fetch(`/api/suggest?q=${encodeURIComponent(q)}`);
        if (!res.ok) return;
        const items = await res.json();
        if (!items.length) { hideSuggestions(); return; }
        suggestBox.innerHTML = "";
        items.forEach(item => {
            const div = document.createElement("div");
            div.className = "suggest-item";
            const isJA = Number(item.is_jan_aushadhi) === 1;
            div.innerHTML = `
                <span class="suggest-name">${escapeHtml(item.brand_name)}</span>
                <span class="suggest-meta">${escapeHtml(item.manufacturer)} &middot; <strong style="white-space:nowrap;">INR ${Number(item.price_inr).toFixed(2)}</strong>
                ${isJA ? ' <span class="tag ja" style="font-size:0.7rem;padding:0.15rem 0.4rem;">Jan Aushadhi</span>' : ''}
                </span>
            `;
            div.addEventListener("click", () => {
                brandInput.value = item.brand_name;
                hideSuggestions();
                searchBrand();
            });
            suggestBox.appendChild(div);
        });
        suggestBox.classList.remove("hidden");
    } catch (e) {
        hideSuggestions();
    }
}

function hideSuggestions() {
    suggestBox.innerHTML = "";
    suggestBox.classList.add("hidden");
}
