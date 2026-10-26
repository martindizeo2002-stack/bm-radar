// Proxy servidor -> hub (evita CORS desde el radar). El radar es público desde el 29-sep-2026 (sin contraseña),
// así que este proxy SOLO permite altas nuevas en el tab Ideas con ID "radar-...": nunca edita ni borra filas existentes.
// Env: HUB_KEY (clave del hub, para reenviar), HUB_URL (función panel del hub).
export default async (req) => {
  if (req.method !== 'POST') return new Response('Método no permitido', { status: 405 });
  let body;
  try { body = await req.json(); } catch { return new Response(JSON.stringify({ error: 'JSON inválido' }), { status: 400 }); }
  const d = body && body.data;
  if (body.action !== 'cadd' || body.tab !== 'Ideas' || !d || typeof d.ID !== 'string' || !d.ID.startsWith('radar-')) {
    return new Response(JSON.stringify({ error: 'solo altas nuevas del radar en Ideas' }), { status: 400 });
  }
  // columnas reales del Sheet (no existe 'Fuente': el link a la pieza original va en Referencias)
  const permitidos = ['ID', 'Canal', 'Titulo', 'Cuadrante', 'Angulo', 'Formato', 'Estado', 'Creada', 'Referencias', 'Notas', 'Guion'];
  const data = Object.fromEntries(Object.entries(d).filter(([k, v]) => permitidos.includes(k) && typeof v === 'string').map(([k, v]) => [k, v.slice(0, k === 'Guion' ? 6000 : 500)]));
  data.Estado = 'Idea';
  const hub = process.env.HUB_URL || 'https://bm-hub-ventas.netlify.app/.netlify/functions/panel';
  try {
    const r = await fetch(hub, { method: 'POST', headers: { 'x-hub-key': process.env.HUB_KEY || '', 'content-type': 'application/json' },
      body: JSON.stringify({ token: 'impo2026-panel', action: 'cadd', tab: 'Ideas', data }) });
    return new Response(await r.text(), { status: r.status, headers: { 'content-type': 'application/json' } });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), { status: 502, headers: { 'content-type': 'application/json' } });
  }
};
export const config = { path: '/api/kanban' };
