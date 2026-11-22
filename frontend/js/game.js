// Lógica pura del cliente (sin DOM): se prueba con `node --test tests/frontend`.

export const WORD_LENGTH = 5;
export const MAX_ATTEMPTS = 6;

const RANK = { absent: 1, present: 2, correct: 3 };
const EMOJI = { correct: "🟩", present: "🟨", absent: "⬛" };

/** Letra válida en minúscula sin tilde (la ñ se conserva), o null. */
export function toLetter(ch) {
  if (typeof ch !== "string" || ch.length !== 1) return null;
  const s = ch.toLowerCase();
  if (s === "ñ") return "ñ";
  const base = s.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  return /^[a-z]$/.test(base) ? base : null;
}

/** Mejor estado conocido de cada letra del teclado (correct > present > absent). */
export function mergeKeyStates(states, guess, result) {
  const next = { ...states };
  [...guess].forEach((letter, i) => {
    const cur = next[letter];
    if (!cur || RANK[result[i]] > RANK[cur]) next[letter] = result[i];
  });
  return next;
}

export function buildShareText(puzzleNumber, guesses, won) {
  const score = won ? guesses.length : "X";
  const rows = guesses.map((g) => g.result.map((c) => EMOJI[c]).join(""));
  return [`Parlache del día${puzzleNumber >= 1 ? ` #${puzzleNumber}` : ""} ${score}/${MAX_ATTEMPTS}`, ...rows].join("\n");
}

export function formatCountdown(seconds) {
  const s = Math.max(0, Math.floor(seconds));
  const p = (n) => String(n).padStart(2, "0");
  return `${p(Math.floor(s / 3600))}:${p(Math.floor((s % 3600) / 60))}:${p(s % 60)}`;
}

/** Fecha de Colombia (UTC−5, sin horario de verano) en formato YYYY-MM-DD. */
export function bogotaDate(now = new Date()) {
  return new Date(now.getTime() - 5 * 3600 * 1000).toISOString().slice(0, 10);
}

const SPOKEN = { correct: "correcta", present: "en otra posición", absent: "no está" };
export const spokenState = (state) => SPOKEN[state] || "vacía";
