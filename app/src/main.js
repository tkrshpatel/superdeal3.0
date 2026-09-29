import './style.css';

const API_BASE = (globalThis.__SUPERDEAL_API__ || '').replace(/\/$/, '');

const categories = ['🔥 Trending', '📉 Price Drops', '💰 Under ₹499', '🏷️ 50%+ Off', '⏰ Ending Soon'];

const app = document.querySelector('#app');
app.innerHTML = `
  <header class="topbar"><div><div class="brand">SuperDeal</div><div class="tagline">Find it. Compare it. Grab it.</div></div><button class="icon-button" aria-label="Notifications">🔔</button></header>
  <main><section class="search-wrap"><input id="search" type="search" placeholder="Search deals, products or brands" autocomplete="off" /></section>
  <section class="chips" aria-label="Deal filters">${categories.map((item, i) => `<button class="chip ${i === 0 ? 'selected' : ''}" data-filter="${i}">${item}</button>`).join('')}</section>
  <section class="section-head"><h1>🔥 Hot deals</h1><span id="count"></span></section><section id="deals" class="deal-list" aria-live="polite"><div class="loading">Finding deals…</div></section></main>
  <nav class="bottom-nav"><button class="active">🏠<span>Home</span></button><button>🔎<span>Search</span></button><button>❤️<span>Saved</span></button></nav>`;

const dealsEl = document.querySelector('#deals');
const countEl = document.querySelector('#count');
const searchEl = document.querySelector('#search');

function escapeHtml(value) { return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

function dealCard(deal) {
  const price = deal.current_price == null ? 'Check price' : `₹${Number(deal.current_price).toLocaleString('en-IN')}`;
  const image = deal.image_url || 'https://placehold.co/96x96?text=Deal';
  const href = deal.affiliate_url || deal.source_url || '#';
  return `<article class="deal-card"><img src="${escapeHtml(image)}" alt="" loading="lazy" /><div class="deal-body"><div class="merchant">${escapeHtml(deal.merchant || 'Deal')}</div><h2>${escapeHtml(deal.product_name)}</h2><div class="price-row"><strong>${price}</strong>${deal.verified_price ? '<span class="verified">✓ verified</span>' : ''}</div><a class="get-deal" href="${escapeHtml(href)}" target="_blank" rel="noopener">GET DEAL →</a></div></article>`;
}

async function loadDeals() {
  dealsEl.innerHTML = '<div class="loading">Finding deals…</div>';
  const q = searchEl.value.trim();
  const query = q ? `?q=${encodeURIComponent(q)}&limit=30` : '?limit=30';
  try {
    const response = await fetch(`${API_BASE}/deals${query}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    countEl.textContent = `${data.deals.length} deals`;
    dealsEl.innerHTML = data.deals.length ? data.deals.map(dealCard).join('') : '<div class="empty">No matching deals yet.</div>';
  } catch { countEl.textContent = ''; dealsEl.innerHTML = '<div class="empty"><strong>SuperDeal is warming up.</strong><br>Connect the API to load live deals.</div>'; }
}

let timer;
searchEl.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(loadDeals, 250); });
document.querySelectorAll('.chip').forEach(chip => chip.addEventListener('click', () => { document.querySelectorAll('.chip').forEach(c => c.classList.remove('selected')); chip.classList.add('selected'); }));
if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {});
loadDeals();
