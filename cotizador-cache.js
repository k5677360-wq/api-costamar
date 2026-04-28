/**
 * COSTAMAR — Cache localStorage + Loading Progresivo
 * Integra este archivo en tu HTML: <script src="cotizador-cache.js"></script>
 */

// ==========================================
// MÓDULO DE CACHÉ EN LOCALSTORAGE
// ==========================================
const CostamarCache = {
  TTL: 5 * 60 * 1000, // 5 minutos (igual que el backend)
  PREFIX: 'costamar_v1_',

  _key(origen, destino, fecha, adultos) {
    return `${this.PREFIX}${origen}_${destino}_${fecha}_${adultos}`;
  },

  get(origen, destino, fecha, adultos) {
    try {
      const key = this._key(origen, destino, fecha, adultos);
      const raw = localStorage.getItem(key);
      if (!raw) return null;
      const { data, ts } = JSON.parse(raw);
      if (Date.now() - ts > this.TTL) {
        localStorage.removeItem(key);
        return null;
      }
      return data;
    } catch {
      return null;
    }
  },

  set(origen, destino, fecha, adultos, data) {
    try {
      const key = this._key(origen, destino, fecha, adultos);
      localStorage.setItem(key, JSON.stringify({ data, ts: Date.now() }));
    } catch (e) {
      // localStorage lleno — limpiar entradas viejas
      this.purge();
    }
  },

  purge() {
    try {
      Object.keys(localStorage)
        .filter(k => k.startsWith(this.PREFIX))
        .forEach(k => localStorage.removeItem(k));
    } catch {}
  },

  isCached(origen, destino, fecha, adultos) {
    return this.get(origen, destino, fecha, adultos) !== null;
  }
};


// ==========================================
// LOADING PROGRESIVO
// ==========================================
const CostamarLoader = {
  // IDs de los elementos HTML en tu página
  CONTAINER_ID: 'resultados-container',
  LOADER_ID: 'cotizador-loader',
  STEPS: [
    { msg: 'Conectando con Costamar...', pct: 15 },
    { msg: 'Buscando disponibilidad...', pct: 40 },
    { msg: 'Comparando tarifas...', pct: 65 },
    { msg: 'Ordenando por precio...', pct: 85 },
    { msg: 'Casi listo...', pct: 95 },
  ],

  _timer: null,
  _stepIdx: 0,

  /**
   * Inserta el HTML del loader si no existe.
   * Llama a esto al iniciar tu app, o simplemente deja que show() lo cree.
   */
  init() {
    if (document.getElementById(this.LOADER_ID)) return;
    const el = document.createElement('div');
    el.id = this.LOADER_ID;
    el.style.cssText = 'display:none;';
    el.innerHTML = `
      <div class="cm-loader-box">
        <div class="cm-plane-wrap">
          <svg class="cm-plane" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M21 16v-2l-8-5V3.5A1.5 1.5 0 0 0 11.5 2a1.5 1.5 0 0 0-1.5 1.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z" fill="currentColor"/>
          </svg>
          <div class="cm-trail"></div>
        </div>
        <p class="cm-loader-msg" id="cm-loader-msg">Buscando vuelos...</p>
        <div class="cm-bar-wrap">
          <div class="cm-bar-fill" id="cm-bar-fill"></div>
        </div>
        <p class="cm-loader-sub" id="cm-loader-sub">Primera búsqueda: 5-8 seg</p>
      </div>
    `;
    document.body.appendChild(el);

    // Inyectar estilos si no están en el CSS
    if (!document.getElementById('cm-loader-styles')) {
      const style = document.createElement('style');
      style.id = 'cm-loader-styles';
      style.textContent = `
        #cotizador-loader {
          position: fixed; inset: 0; z-index: 9999;
          display: flex; align-items: center; justify-content: center;
          background: rgba(0,0,0,0.45);
        }
        .cm-loader-box {
          background: #fff; border-radius: 16px; padding: 2.5rem 2rem;
          min-width: 300px; max-width: 380px; text-align: center;
          box-shadow: 0 8px 32px rgba(0,0,0,0.18);
        }
        .cm-plane-wrap {
          position: relative; height: 56px; display: flex;
          align-items: center; justify-content: center; margin-bottom: 1.25rem;
        }
        .cm-plane {
          width: 40px; height: 40px; color: #1a56db;
          animation: cm-fly 1.6s ease-in-out infinite;
        }
        @keyframes cm-fly {
          0%,100% { transform: translateY(0) rotate(-10deg); }
          50%      { transform: translateY(-10px) rotate(5deg); }
        }
        .cm-trail {
          position: absolute; left: 50%; bottom: 8px;
          width: 60px; height: 3px; margin-left: -10px;
          background: linear-gradient(90deg,transparent,#93c5fd);
          border-radius: 3px; opacity: 0.7;
          animation: cm-trail 1.6s ease-in-out infinite;
        }
        @keyframes cm-trail {
          0%,100% { width: 30px; opacity: 0.4; }
          50%      { width: 70px; opacity: 0.8; }
        }
        .cm-loader-msg {
          font-size: 16px; font-weight: 600; color: #111827; margin: 0 0 .5rem;
        }
        .cm-loader-sub {
          font-size: 12px; color: #6b7280; margin: .5rem 0 0;
        }
        .cm-bar-wrap {
          background: #e5e7eb; border-radius: 999px; height: 6px;
          overflow: hidden; margin-top: 1rem;
        }
        .cm-bar-fill {
          height: 100%; border-radius: 999px;
          background: #1a56db; width: 0%;
          transition: width 0.6s ease;
        }
        /* Caché badge */
        .cm-badge-cache {
          display: inline-flex; align-items: center; gap: 5px;
          background: #ecfdf5; color: #065f46;
          border: 1px solid #6ee7b7; border-radius: 999px;
          font-size: 12px; font-weight: 600; padding: 3px 10px;
          margin-bottom: 12px; animation: cm-fadein .3s ease;
        }
        @keyframes cm-fadein { from { opacity:0; transform:translateY(-4px); } }
      `;
      document.head.appendChild(style);
    }
  },

  show(fromCache = false) {
    this.init();
    this._stepIdx = 0;
    const el = document.getElementById(this.LOADER_ID);
    if (!el) return;
    el.style.display = 'flex';

    const msgEl = document.getElementById('cm-loader-msg');
    const subEl = document.getElementById('cm-loader-sub');
    const barEl = document.getElementById('cm-bar-fill');

    if (fromCache) {
      if (msgEl) msgEl.textContent = 'Cargando desde caché...';
      if (subEl) subEl.textContent = 'Respuesta instantánea ⚡';
      if (barEl) barEl.style.width = '100%';
      return;
    }

    // Avanzar pasos progresivamente
    const nextStep = () => {
      if (this._stepIdx >= this.STEPS.length) return;
      const { msg, pct } = this.STEPS[this._stepIdx];
      if (msgEl) msgEl.textContent = msg;
      if (barEl) barEl.style.width = `${pct}%`;
      if (subEl && this._stepIdx === 0) subEl.textContent = 'Primera búsqueda: 5-8 seg';
      this._stepIdx++;
      const delay = 800 + Math.random() * 600;
      this._timer = setTimeout(nextStep, delay);
    };

    nextStep();
  },

  hide() {
    clearTimeout(this._timer);
    const el = document.getElementById(this.LOADER_ID);
    if (!el) return;
    const barEl = document.getElementById('cm-bar-fill');
    if (barEl) barEl.style.width = '100%';
    setTimeout(() => { el.style.display = 'none'; }, 300);
  }
};


// ==========================================
// FUNCIÓN PRINCIPAL — reemplaza tu fetch
// ==========================================
/**
 * Busca vuelos con caché localStorage + loading progresivo.
 *
 * @param {string} origen   - Nombre ciudad (ej: "Lima")
 * @param {string} destino  - Nombre ciudad (ej: "Cusco")
 * @param {string} fecha    - YYYY-MM-DD
 * @param {number} adultos
 * @param {string} apiUrl   - URL de tu API (ej: "https://tu-app.onrender.com")
 * @returns {Promise<Array>} - Array de vuelos
 */
async function buscarVuelosConCache(origen, destino, fecha, adultos = 1, apiUrl = '') {
  const cached = CostamarCache.get(origen, destino, fecha, adultos);

  if (cached) {
    CostamarLoader.show(true); // loader rápido
    await new Promise(r => setTimeout(r, 400)); // pequeña pausa visual
    CostamarLoader.hide();
    console.log('⚡ Desde caché localStorage');
    return cached;
  }

  CostamarLoader.show(false); // loader progresivo real

  try {
    const res = await fetch(`${apiUrl}/api/cotizar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ origen, destino, fechaIda: fecha, adultos })
    });

    const json = await res.json();

    if (!json.success) throw new Error(json.error || 'Sin resultados');

    CostamarCache.set(origen, destino, fecha, adultos, json.vuelos);
    CostamarLoader.hide();
    return json.vuelos;

  } catch (err) {
    CostamarLoader.hide();
    throw err;
  }
}

/**
 * Muestra un badge verde "Resultados desde caché" encima de los resultados.
 * Pásale el ID del contenedor donde mostrás los vuelos.
 */
function mostrarBadgeCache(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const old = container.querySelector('.cm-badge-cache');
  if (old) old.remove();
  const badge = document.createElement('div');
  badge.className = 'cm-badge-cache';
  badge.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none"><path d="M5 12l5 5L20 7" stroke="currentColor" stroke-width="3" stroke-linecap="round"/></svg> Resultados desde caché`;
  container.insertBefore(badge, container.firstChild);
}

// Exportar para módulos ES
if (typeof module !== 'undefined') {
  module.exports = { CostamarCache, CostamarLoader, buscarVuelosConCache, mostrarBadgeCache };
}
