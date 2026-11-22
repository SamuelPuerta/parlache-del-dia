import * as api from "./api.js";
import {
  WORD_LENGTH, toLetter, mergeKeyStates, buildShareText, bogotaDate,
} from "./game.js";
import * as ui from "./ui.js";
import { initScene, setMood } from "./scene.js";

const CONTRAST_KEY = "parlache.contrast";

const state = {
  date: null,
  puzzle: 0,
  status: "playing",   // playing | won | lost
  guesses: [],         // [{ guess, result }]
  current: "",
  keys: {},
  reveal: null,
  player: { alias: "", current_streak: 0, best_streak: 0 },
  busy: false,
  loaded: false,
  rankingType: "daily",
};

const $ = (id) => document.getElementById(id);

// ---------- carga ----------

async function loadToday() {
  ui.showOffline(false);
  try {
    const t = await api.getToday();
    applyToday(t);
  } catch (e) {
    if (!state.loaded) ui.showOffline(true);
    else ui.toast(messageFor(e));
  }
}

function applyToday(t) {
  state.date = t.date;
  state.puzzle = t.puzzle_number;
  state.status = t.state.status;
  state.guesses = t.state.guesses;
  state.reveal = t.state.reveal;
  state.player = t.player;
  state.current = "";
  state.keys = {};
  state.loaded = true;

  ui.buildBoard();
  state.guesses.forEach((g, r) => {
    ui.revealRow(r, g.guess, g.result, false);
    state.keys = mergeKeyStates(state.keys, g.guess, g.result);
  });
  ui.setKeyStates(state.keys);
  ui.setPuzzle(state.puzzle);
  ui.setStreak(state.player.current_streak);
  ui.setBusy(false);
  setMood(state.status === "playing" ? null : state.status);

  if (state.status !== "playing") {
    ui.showResultButton(true);
    ui.renderEnd({ won: state.status === "won", reveal: state.reveal, player: state.player });
    ui.startCountdown(t.seconds_to_next, () => {});
    setTimeout(() => { if (!ui.isDialogOpen()) ui.openDialog("dlg-end"); }, 900);
  } else {
    ui.showResultButton(false);
    ui.startCountdown(t.seconds_to_next, () => {});
  }
}

// ---------- entrada ----------

function canType() {
  return state.loaded && state.status === "playing" && !state.busy && !ui.isDialogOpen();
}

function onKey(key) {
  if (!canType()) {
    if (state.loaded && state.status !== "playing" && !ui.isDialogOpen()) ui.toast("Ya terminaste hoy");
    return;
  }
  if (key === "enter") return submit();
  if (key === "back") {
    if (!state.current) return;
    state.current = state.current.slice(0, -1);
    ui.setTile(state.guesses.length, state.current.length, "");
    return;
  }
  if (state.current.length >= WORD_LENGTH) return;
  ui.setTile(state.guesses.length, state.current.length, key);
  state.current += key;
}

document.addEventListener("keydown", (e) => {
  if (e.ctrlKey || e.metaKey || e.altKey || e.isComposing) return;
  const onButton = e.target.closest && e.target.closest("button");
  if (e.key === "Enter" || e.key === " ") {
    if (onButton) return;           // el botón enfocado hace su trabajo
    if (e.key === "Enter") { e.preventDefault(); onKey("enter"); }
    return;
  }
  if (e.key === "Backspace") { e.preventDefault(); onKey("back"); return; }
  if (e.key.length !== 1) return;
  const letter = toLetter(e.key);
  if (letter) onKey(letter);
  else if (canType()) ui.toast("Solo letras");
});

// ---------- envío ----------

async function submit() {
  const r = state.guesses.length;
  if (state.current.length < WORD_LENGTH) {
    ui.shakeRow(r);
    ui.toast("Faltan letras");
    return;
  }
  state.busy = true;
  ui.setBusy(true);
  const guess = state.current;
  try {
    const res = await api.postGuess(guess);
    state.guesses.push({ guess, result: res.result });
    state.current = "";
    state.player = { ...state.player, ...res.player };
    await ui.revealRow(r, guess, res.result, true);
    state.keys = mergeKeyStates(state.keys, guess, res.result);
    ui.setKeyStates(state.keys);
    if (res.status !== "playing") finish(res, r);
  } catch (e) {
    handleError(e, r);
  } finally {
    state.busy = false;
    ui.setBusy(false);
  }
}

function finish(res, row) {
  state.status = res.status;
  state.reveal = res.reveal;
  const won = res.status === "won";
  ui.setStreak(state.player.current_streak);
  ui.renderEnd({ won, reveal: res.reveal, player: state.player });
  api.getToday().then((t) => ui.startCountdown(t.seconds_to_next, () => {})).catch(() => ui.startCountdown(3600, () => {}));
  setMood(res.status);
  if (won) ui.waveRow(row);
  setTimeout(() => { ui.showResultButton(true); ui.openDialog("dlg-end"); }, won ? 1300 : 900);
}

function messageFor(e) {
  return {
    network: "Sin conexión. Revisa tu internet e intenta de nuevo",
    throttled: "Vas muy rápido. Espera un momento e intenta de nuevo",
    invalid_guess: "Solo letras, sin números ni símbolos",
    game_over: "Ya terminaste hoy",
    conflict: "Se cruzó un intento. Intenta de nuevo",
  }[e.code] || "Algo falló de nuestro lado. Intenta de nuevo";
}

function handleError(e, row) {
  ui.toast(messageFor(e));
  if (e.code === "invalid_guess") ui.shakeRow(row);
  if (e.code === "game_over" || e.code === "conflict") loadToday();
}

// ---------- ranking, compartir, contraste ----------

async function openRanking(type = state.rankingType) {
  state.rankingType = type;
  ui.setRankingTab(type);
  ui.renderRankingState("loading");
  ui.openDialog("dlg-ranking");
  try {
    ui.renderRanking(await api.getRanking(type), state.player.alias);
  } catch {
    ui.renderRankingState("error");
  }
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.className = "sr-copy";
    document.body.append(ta);
    ta.select();
    let ok = false;
    try { ok = document.execCommand("copy"); } catch { /* sin portapapeles */ }
    ta.remove();
    return ok;
  }
}

async function share() {
  const text = buildShareText(state.puzzle, state.guesses, state.status === "won");
  ui.toast((await copyText(text)) ? "Resultado copiado" : "No se pudo copiar");
}

function toggleContrast() {
  const on = document.documentElement.dataset.contrast !== "high";
  ui.setContrast(on);
  try { localStorage.setItem(CONTRAST_KEY, on ? "high" : "normal"); } catch { /* opcional */ }
}

// ---------- arranque ----------

function firstVisit() {
  try {
    if (localStorage.getItem("parlache.seenHelp")) return false;
    localStorage.setItem("parlache.seenHelp", "1");
  } catch { /* sin almacenamiento: se muestra solo esta vez */ }
  return true;
}

function init() {
  let saved = null;
  try { saved = localStorage.getItem(CONTRAST_KEY); } catch { /* opcional */ }
  ui.setContrast(saved === "high");

  ui.buildBoard();
  ui.buildKeyboard(onKey);
  ui.initDialogs();
  initScene($("scene"));
  requestAnimationFrame(() => document.body.classList.add("is-ready"));

  $("btn-help").addEventListener("click", () => ui.openDialog("dlg-help"));
  $("btn-ranking").addEventListener("click", () => openRanking());
  $("btn-contrast").addEventListener("click", toggleContrast);
  $("btn-retry").addEventListener("click", loadToday);
  $("btn-result").addEventListener("click", () => ui.openDialog("dlg-end"));
  $("btn-share").addEventListener("click", share);
  $("btn-end-ranking").addEventListener("click", () => { ui.closeDialog($("dlg-end")); openRanking(); });
  document.querySelectorAll(".tabs [role=tab]").forEach((t) =>
    t.addEventListener("click", () => openRanking(t.dataset.type)));

  // Si la pestaña estuvo dormida y cambió el día (hora de Colombia), se recarga el estado.
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && state.loaded && bogotaDate() !== state.date) loadToday();
  });

  loadToday().then(() => {
    if (state.loaded && state.status === "playing" && state.guesses.length === 0 && firstVisit()) {
      setTimeout(() => { if (!ui.isDialogOpen()) ui.openDialog("dlg-help"); }, 1800);
    }
  });
}

init();
