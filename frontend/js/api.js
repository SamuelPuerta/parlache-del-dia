// Cliente de la API. Mismo origen (/api): CloudFront reparte hacia API Gateway.

const KEY = "parlache.playerId";
const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const TIMEOUT_MS = 12000;

export class ApiError extends Error {
  constructor(code, status = 0) {
    super(code);
    this.code = code;
    this.status = status;
  }
}

export function uuidv4() {
  if (globalThis.crypto && crypto.randomUUID) return crypto.randomUUID();
  const b = new Uint8Array(16);
  if (globalThis.crypto && crypto.getRandomValues) crypto.getRandomValues(b);
  else for (let i = 0; i < 16; i++) b[i] = Math.floor(Math.random() * 256);
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = [...b].map((x) => x.toString(16).padStart(2, "0")).join("");
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}

let memoryId = null;

export function getPlayerId() {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved && UUID_V4.test(saved)) return saved;
  } catch { /* almacenamiento bloqueado */ }
  if (!memoryId) memoryId = uuidv4();
  try { localStorage.setItem(KEY, memoryId); } catch { /* sigue en memoria */ }
  return memoryId;
}

async function request(path, options = {}) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  let res;
  try {
    res = await fetch(path, {
      ...options,
      signal: ctrl.signal,
      headers: { "X-Player-Id": getPlayerId(), "Content-Type": "application/json" },
    });
  } catch {
    throw new ApiError("network");
  } finally {
    clearTimeout(timer);
  }
  let data = null;
  try { data = await res.json(); } catch { /* cuerpo vacío o no JSON */ }
  if (!res.ok) {
    const code = (data && data.error) || (res.status === 429 ? "throttled" : "internal");
    throw new ApiError(code, res.status);
  }
  return data;
}

export const getToday = () => request("/api/today");
export const postGuess = (guess) => request("/api/guess", { method: "POST", body: JSON.stringify({ guess }) });
export const getRanking = (type) => request(`/api/ranking?type=${encodeURIComponent(type)}`);
