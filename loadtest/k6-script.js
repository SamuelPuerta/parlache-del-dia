// Prueba de carga (sección 9.4): rampa 20 -> 50 usuarios virtuales durante 2 minutos.
// Uso: k6 run -e BASE_URL=https://d3n55jo239aice.cloudfront.net loadtest/k6-script.js
import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.BASE_URL;
if (!BASE_URL) throw new Error("Falta -e BASE_URL=https://<dominio>.cloudfront.net");

export const options = {
  stages: [
    { duration: "30s", target: 20 },
    { duration: "60s", target: 50 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    // Los 429 son esperados (throttling); se cuentan como correctos.
    checks: ["rate>0.95"],
    http_req_duration: ["p(95)<2000"],
  },
};

function uuidv4() {
  const h = "0123456789abcdef";
  let s = "";
  for (let i = 0; i < 36; i++) {
    if (i === 8 || i === 13 || i === 18 || i === 23) s += "-";
    else if (i === 14) s += "4";
    else if (i === 19) s += "89ab"[Math.floor(Math.random() * 4)];
    else s += h[Math.floor(Math.random() * 16)];
  }
  return s;
}

function randomWord() {
  const a = "abcdefghijklmnopqrstuvwxyz";
  let w = "";
  for (let i = 0; i < 5; i++) w += a[Math.floor(Math.random() * a.length)];
  return w;
}

const ok = (r) => r.status === 200 || r.status === 429 || r.status === 409;

export default function () {
  const headers = { "X-Player-Id": uuidv4(), "Content-Type": "application/json" };

  const today = http.get(`${BASE_URL}/api/today`, { headers });
  check(today, { "today 200/429": ok });
  sleep(0.5);

  const guesses = 3 + Math.floor(Math.random() * 4); // 3 a 6
  for (let i = 0; i < guesses; i++) {
    const r = http.post(`${BASE_URL}/api/guess`, JSON.stringify({ guess: randomWord() }), { headers });
    check(r, { "guess 200/409/429": ok });
    sleep(0.5 + Math.random());
  }

  const rank = http.get(`${BASE_URL}/api/ranking`, { headers });
  check(rank, { "ranking 200/429": ok });
  sleep(1);
}
