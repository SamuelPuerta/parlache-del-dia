// Todo lo que toca el DOM. Los estilos se cambian con clases (CSP sin estilos en línea).
import { WORD_LENGTH, MAX_ATTEMPTS, spokenState, formatCountdown } from "./game.js";

const $ = (id) => document.getElementById(id);
const reduce = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

const KEYS = [
  ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"],
  ["a", "s", "d", "f", "g", "h", "j", "k", "l", "ñ"],
  ["enter", "z", "x", "c", "v", "b", "n", "m", "back"],
];
const BACK_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6H9l-6 6 6 6h11a1 1 0 0 0 1-1V7a1 1 0 0 0-1-1ZM13 10l4 4M17 10l-4 4"/></svg>';

let rows = [];
let keyEls = {};

// ---------- tablero y teclado ----------

export function buildBoard() {
  const board = $("board");
  board.replaceChildren();
  rows = [];
  for (let r = 0; r < MAX_ATTEMPTS; r++) {
    const row = document.createElement("div");
    row.className = "row";
    row.setAttribute("role", "row");
    const tiles = [];
    for (let c = 0; c < WORD_LENGTH; c++) {
      const t = document.createElement("div");
      t.className = "tile";
      t.setAttribute("role", "gridcell");
      t.style.setProperty("--i", c);
      t.setAttribute("aria-label", `Fila ${r + 1}, columna ${c + 1}, vacía`);
      row.append(t);
      tiles.push(t);
    }
    board.append(row);
    rows.push({ row, tiles });
  }
}

export function buildKeyboard(onKey) {
  const kb = $("keyboard");
  kb.replaceChildren();
  keyEls = {};
  for (const line of KEYS) {
    const div = document.createElement("div");
    div.className = "krow";
    for (const k of line) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "key";
      b.dataset.key = k;
      if (k === "enter") { b.textContent = "Enviar"; b.classList.add("wide"); b.setAttribute("aria-label", "Enviar intento"); }
      else if (k === "back") { b.innerHTML = BACK_ICON; b.classList.add("wide"); b.setAttribute("aria-label", "Borrar"); }
      else { b.textContent = k; keyEls[k] = b; }
      b.addEventListener("click", () => { onKey(k); b.blur(); });
      div.append(b);
    }
    kb.append(div);
  }
}

export function setTile(r, c, letter) {
  const t = rows[r].tiles[c];
  t.textContent = letter || "";
  t.classList.toggle("filled", !!letter);
  t.setAttribute("aria-label", letter ? `Fila ${r + 1}, letra ${letter}` : `Fila ${r + 1}, columna ${c + 1}, vacía`);
  if (letter) { t.classList.remove("filled"); void t.offsetWidth; t.classList.add("filled"); }
}

function paintTile(tile, r, c, letter, state) {
  tile.classList.remove("filled", "t-correct", "t-present", "t-absent");
  tile.classList.add(`t-${state}`);
  tile.setAttribute("aria-label", `Fila ${r + 1}, letra ${letter}, ${spokenState(state)}`);
}

/** Pinta una fila con el resultado del servidor. Devuelve una promesa que termina cuando acaba la animación. */
export function revealRow(r, guess, result, animate) {
  const { tiles } = rows[r];
  [...guess].forEach((l, c) => { tiles[c].textContent = l; });
  if (!animate || reduce()) {
    tiles.forEach((t, c) => paintTile(t, r, c, guess[c], result[c]));
    return Promise.resolve();
  }
  tiles.forEach((t, c) => {
    t.classList.add("flip");
    setTimeout(() => paintTile(t, r, c, guess[c], result[c]), c * 260 + 310);
  });
  return new Promise((res) => setTimeout(() => {
    tiles.forEach((t) => t.classList.remove("flip"));
    res();
  }, (WORD_LENGTH - 1) * 260 + 640));
}

export function shakeRow(r) {
  const el = rows[r].row;
  el.classList.remove("shake");
  void el.offsetWidth;
  el.classList.add("shake");
  setTimeout(() => el.classList.remove("shake"), 480);
}

export function waveRow(r) {
  if (reduce()) return;
  rows[r].row.classList.add("wave");
}

export function setKeyStates(states) {
  for (const [letter, state] of Object.entries(states)) {
    const k = keyEls[letter];
    if (!k) continue;
    k.classList.remove("k-correct", "k-present", "k-absent");
    k.classList.add(`k-${state}`);
    k.setAttribute("aria-label", `${letter}, ${spokenState(state)}`);
  }
}

export function setBusy(busy) {
  $("board").setAttribute("aria-busy", String(busy));
  document.querySelectorAll(".key").forEach((k) => { k.disabled = busy; });
}

// ---------- cabecera, avisos y estados ----------

export function setPuzzle(n) { $("puzzle-no").textContent = n >= 1 ? `Día ${n}` : "Versión de prueba"; }

export function setStreak(n) {
  const chip = $("streak-chip");
  chip.hidden = !(n > 0);
  chip.textContent = `Racha ${n}`;
}

export function showOffline(show) {
  $("offline").hidden = !show;
  $("board").hidden = show;
  $("keyboard").hidden = show;
}

export function showResultButton(show) { $("btn-result").hidden = !show; }

export function toast(text) {
  const box = $("toasts");
  while (box.children.length > 2) box.firstChild.remove();
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = text;
  box.append(el);
  setTimeout(() => {
    el.classList.add("out");
    setTimeout(() => el.remove(), 320);
  }, 2200);
}

export function setContrast(on) {
  document.documentElement.dataset.contrast = on ? "high" : "normal";
  $("btn-contrast").setAttribute("aria-pressed", String(on));
}

// ---------- ventanas ----------

export function openDialog(id) {
  const d = $(id);
  d.classList.remove("closing");
  if (!d.open) d.showModal();
  d.focus({ preventScroll: true });   // evita que el foco caiga (con anillo) sobre el botón de cerrar
}

export function closeDialog(d) {
  if (!d.open) return;
  if (reduce()) { d.close(); return; }
  d.classList.add("closing");
  setTimeout(() => { d.classList.remove("closing"); d.close(); }, 220);
}

export function initDialogs() {
  document.querySelectorAll("dialog").forEach((d) => {
    d.tabIndex = -1;
    d.addEventListener("click", (e) => { if (e.target === d) closeDialog(d); });
    d.addEventListener("cancel", (e) => { e.preventDefault(); closeDialog(d); });
    d.querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", () => closeDialog(d)));
  });
}

export function isDialogOpen() {
  return [...document.querySelectorAll("dialog")].some((d) => d.open);
}

export function renderEnd({ won, reveal, player }) {
  const dlg = $("dlg-end");
  dlg.classList.toggle("end-won", won);
  dlg.classList.toggle("end-lost", !won);

  $("h-end").textContent = won ? "¡Ese es el parlache!" : "Hoy no fue";
  $("end-word").textContent = reveal.word;
  $("end-meaning").textContent = reveal.meaning;

  const ex = $("end-example");
  ex.textContent = reveal.example ? `“${reveal.example}”` : "";
  ex.hidden = !reveal.example;

  const region = $("end-region");
  region.textContent = reveal.region ? `Se dice en ${reveal.region}` : "";
  region.hidden = !reveal.region;

  $("end-quote").hidden = !reveal.example && !reveal.region;

  $("end-streak").textContent = player.current_streak;
  $("end-best").textContent = player.best_streak;
}

let timer = 0;
export function startCountdown(seconds, onZero) {
  clearInterval(timer);
  const end = Date.now() + seconds * 1000;
  const label = $("end-next");
  const tick = () => {
    const left = Math.max(0, Math.round((end - Date.now()) / 1000));
    if (left === 0) {
      clearInterval(timer);
      label.textContent = "Ya hay palabra nueva";
      onZero();
      return;
    }
    label.textContent = `Próxima palabra en ${formatCountdown(left)}`;
  };
  tick();
  timer = setInterval(tick, 1000);
}

export function setShareLabel(text) { $("btn-share").textContent = text; }

// ---------- ranking ----------

export function renderRankingState(kind) {
  const box = $("rank-list");
  const el = document.createElement("p");
  el.className = kind === "loading" ? "loading" : "empty";
  el.textContent = {
    loading: "Cargando…",
    error: "No pudimos cargar el ranking. Cierra y vuelve a abrirlo.",
  }[kind];
  box.replaceChildren(el);
}

function rankValue(entry, type) {
  return type === "daily"
    ? `${entry.attempts} ${entry.attempts === 1 ? "intento" : "intentos"}`
    : `${entry.streak} ${entry.streak === 1 ? "día" : "días"}`;
}

function podiumEntry(entry, place, type, myAlias) {
  const item = document.createElement("div");
  item.className = `podium-item p${place}`;
  item.style.setProperty("--i", place - 1);
  if (entry.alias === myAlias) item.classList.add("me");

  const rank = document.createElement("span");
  rank.className = "podium-rank";
  rank.textContent = place;

  const who = document.createElement("span");
  who.className = "podium-who";
  const name = document.createElement("span");
  name.className = "name";
  name.textContent = entry.alias;
  who.append(name);

  const val = document.createElement("span");
  val.className = "podium-val";
  val.textContent = rankValue(entry, type);

  item.append(rank);
  if (entry.alias === myAlias) {
    const you = document.createElement("span");
    you.className = "you podium-you";
    you.textContent = "Tú";
    item.append(you);
  }
  item.append(who, val);
  return item;
}

function rankRow(entry, index, type, myAlias) {
  const li = document.createElement("li");
  li.style.setProperty("--i", index);
  if (entry.alias === myAlias) li.classList.add("me");

  const pos = document.createElement("span");
  pos.className = "pos";
  pos.textContent = entry.rank;

  const who = document.createElement("span");
  who.className = "who";
  who.textContent = entry.alias;
  if (entry.alias === myAlias) {
    const you = document.createElement("span");
    you.className = "you";
    you.textContent = "Tú";
    who.append(you);
  }

  const val = document.createElement("span");
  val.className = "val";
  val.textContent = rankValue(entry, type);

  li.append(pos, who, val);
  return li;
}

export function renderRanking(data, myAlias) {
  const box = $("rank-list");
  if (!data.entries.length) {
    const p = document.createElement("p");
    p.className = "empty";
    p.textContent = data.type === "daily"
      ? "Nadie ha ganado hoy todavía. Puedes ser el primero."
      : "Aún no hay rachas activas. Gana hoy para abrir la tuya.";
    box.replaceChildren(p);
    return;
  }

  const frag = document.createDocumentFragment();

  const podium = document.createElement("div");
  podium.className = "podium";
  data.entries.slice(0, 3).forEach((e, i) => {
    podium.append(podiumEntry(e, i + 1, data.type, myAlias));
  });
  frag.append(podium);

  const rest = data.entries.slice(3);
  if (rest.length) {
    const caption = document.createElement("p");
    caption.className = "rank-caption";
    caption.textContent = "Resto de la tabla";
    frag.append(caption);

    const ol = document.createElement("ol");
    ol.className = "rank";
    rest.forEach((e, i) => ol.append(rankRow(e, i, data.type, myAlias)));
    frag.append(ol);
  }

  box.replaceChildren(frag);
}

export function setRankingTab(type) {
  document.querySelectorAll(".tabs [role=tab]").forEach((t) =>
    t.setAttribute("aria-selected", String(t.dataset.type === type)));
}
