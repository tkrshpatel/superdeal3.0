import './style.css';

const API_BASE = (globalThis.__SUPERDEAL_API__ || '').replace(/\/$/, '');
const filters = [
  ['trending', '🔥', 'Trending'], ['drops', '📉', 'Price drops'], ['under499', '₹', 'Under ₹499'],
  ['discount', '%', '50%+ off'], ['ending', '⏳', 'Ending soon']
];
const state = { deals: [], active: 'trending', saved: new Set(JSON.parse(localStorage.getItem('superdeal-saved') || '[]')) };

const app = document.querySelector('#app');
app.innerHTML = `
<header class="topbar"><div class="brand-mark"><span class="logo-dot"></span><div><div class="brand">SuperDeal</div><div class="tagline">Deals worth your click.</div></div></div><button id="notify" class="circle-btn" aria-label="Notifications">♧</button></header>
<main>
<section class="hero"><div class="eyebrow">TODAY'S PICKS</div><h1>Spend less.<br><span>Get more.</span></h1><p>Fresh deals, price drops and genuine finds — all in one place.</p></section>
<section class="search-wrap"><span class="search-icon">⌕</span><input id="search" type="search" placeholder="Search products, brands or deals" autocomplete="off" /><button id="clear" class="clear hidden" aria-label="Clear search">×</button></section>
<section class="chips" aria-label="Deal filters">${filters.map(([id,icon,label],i)=>`<button class="chip ${i===0?'selected':''}" data-filter="${id}"><b>${icon}</b>${label}</button>`).join('')}</section>
<section class="section-head"><div><div class="eyebrow">CURATED FOR YOU</div><h2 id="section-title">Trending now</h2></div><span id="count"></span></section>
<section id="deals" class="deal-grid" aria-live="polite"></section>
</main>
<nav class="bottom-nav"><button class="active" data-nav="home"><span>⌂</span>Home</button><button data-nav="search"><span>⌕</span>Search</button><button data-nav="saved"><span>♡</span>Saved</button></nav>
<div id="toast" class="toast" role="status"></div>`;

const dealsEl = document.querySelector('#deals'), countEl = document.querySelector('#count'), searchEl = document.querySelector('#search'), clearEl = document.querySelector('#clear');
const sectionTitle = document.querySelector('#section-title'), toast = document.querySelector('#toast');
const money = value => value == null ? 'Check price' : `₹${Number(value).toLocaleString('en-IN')}`;
const esc = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function discountBadge(deal) { const d=deal.discount_pct ?? deal.discount; return d ? `<span class="badge">${esc(d)}% OFF</span>` : ''; }
function card(deal) {
  const saved=state.saved.has(String(deal.id));
  const href=deal.affiliate_url||deal.source_url||'#';
  return `<article class="deal-card" data-id="${esc(deal.id)}">
    <div class="image-wrap"><img src="${esc(deal.image_url||'https://placehold.co/320x260?text=SuperDeal')}" alt="${esc(deal.product_name)}" loading="lazy"/><button class="save ${saved?'saved':''}" data-save="${esc(deal.id)}" aria-label="${saved?'Remove from saved':'Save deal'}">${saved?'♥':'♡'}</button>${discountBadge(deal)}</div>
    <div class="card-content"><div class="merchant">${esc(deal.merchant||'SuperDeal find')}</div><h3>${esc(deal.product_name)}</h3><div class="price-line"><strong>${money(deal.current_price)}</strong>${deal.verified_price?'<span class="verified">✓ Verified</span>':''}</div><div class="card-footer"><a class="get-deal" href="${esc(href)}" target="_blank" rel="noopener">Get deal <span>↗</span></a><button class="share" data-share="${esc(deal.id)}" aria-label="Share deal">⌁</button></div></div>
  </article>`;
}
function render(list=state.deals) { countEl.textContent=`${list.length} finds`; dealsEl.innerHTML=list.length?list.map(card).join(''):'<div class="empty"><div>✦</div><strong>No deals found</strong><p>Try another product or filter.</p></div>'; }
function save(id){const key=String(id);state.saved.has(key)?state.saved.delete(key):state.saved.add(key);localStorage.setItem('superdeal-saved',JSON.stringify([...state.saved]));render(filtered());toast.textContent=state.saved.has(key)?'Saved to your deals ♥':'Removed from saved';toast.classList.add('show');setTimeout(()=>toast.classList.remove('show'),1600);}
function filtered(){const q=searchEl.value.trim().toLowerCase();let list=state.deals.filter(d=>!q||String(d.product_name).toLowerCase().includes(q)||String(d.merchant||'').toLowerCase().includes(q));if(state.active==='under499')list=list.filter(d=>d.current_price!=null&&d.current_price<500);if(state.active==='discount')list=list.filter(d=>Number(d.discount_pct??d.discount??0)>=50);return list;}
async function load(){dealsEl.innerHTML='<div class="skeleton-grid">'+Array.from({length:4},()=>'<div class="skeleton"></div>').join('')+'</div>';try{const r=await fetch(`${API_BASE}/deals?limit=30`);if(!r.ok)throw new Error();const data=await r.json();state.deals=data.deals||[];render(filtered());}catch{countEl.textContent='';dealsEl.innerHTML='<div class="empty"><div>⚡</div><strong>We are warming up.</strong><p>Live deals will appear here once the API is connected.</p></div>';}}

document.querySelectorAll('.chip').forEach(c=>c.addEventListener('click',()=>{document.querySelectorAll('.chip').forEach(x=>x.classList.remove('selected'));c.classList.add('selected');state.active=c.dataset.filter;sectionTitle.textContent=c.textContent.trim();render(filtered());}));
searchEl.addEventListener('input',()=>{clearEl.classList.toggle('hidden',!searchEl.value);render(filtered());});clearEl.addEventListener('click',()=>{searchEl.value='';clearEl.classList.add('hidden');render(filtered());searchEl.focus();});
dealsEl.addEventListener('click',e=>{const saveBtn=e.target.closest('[data-save]');if(saveBtn)save(saveBtn.dataset.save);const shareBtn=e.target.closest('[data-share]');if(shareBtn){const d=state.deals.find(x=>String(x.id)===String(shareBtn.dataset.share));if(d&&navigator.share)navigator.share({title:d.product_name,text:`Check this deal on SuperDeal: ${money(d.current_price)}`,url:d.affiliate_url||d.source_url}).catch(()=>{});else{navigator.clipboard?.writeText(d?.affiliate_url||d?.source_url||location.href);toast.textContent='Deal link copied';toast.classList.add('show');setTimeout(()=>toast.classList.remove('show'),1600);}}});
document.querySelectorAll('[data-nav]').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('[data-nav]').forEach(x=>x.classList.remove('active'));b.classList.add('active');if(b.dataset.nav==='search')searchEl.focus();if(b.dataset.nav==='saved'){state.active='saved';sectionTitle.textContent='Saved deals';render(state.deals.filter(d=>state.saved.has(String(d.id))));}}));
if('serviceWorker'in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{});load();
