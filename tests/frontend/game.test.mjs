import test from "node:test";
import assert from "node:assert/strict";
import {
  toLetter, mergeKeyStates, buildShareText, formatCountdown, bogotaDate,
} from "../../frontend/js/game.js";

test("toLetter quita tildes, conserva la ñ y rechaza lo demás", () => {
  assert.equal(toLetter("Á"), "a");
  assert.equal(toLetter("ñ"), "ñ");
  assert.equal(toLetter("Ñ"), "ñ");
  assert.equal(toLetter("ü"), "u");
  assert.equal(toLetter("7"), null);
  assert.equal(toLetter("ab"), null);
  assert.equal(toLetter(" "), null);
});

test("mergeKeyStates nunca degrada el estado de una letra", () => {
  let s = mergeKeyStates({}, "arepa", ["correct", "absent", "present", "absent", "absent"]);
  assert.equal(s.a, "correct");
  s = mergeKeyStates(s, "pelao", ["absent", "present", "absent", "absent", "absent"]);
  assert.equal(s.a, "correct");
  assert.equal(s.p, "absent");
  assert.equal(s.e, "present");
  s = mergeKeyStates(s, "pesos", ["present", "correct", "absent", "absent", "absent"]);
  assert.equal(s.p, "present");
  assert.equal(s.e, "correct");
});

test("buildShareText no incluye la palabra y marca X al perder", () => {
  const g = [{ guess: "pelao", result: ["absent", "present", "absent", "absent", "absent"] },
             { guess: "parce", result: ["correct", "correct", "correct", "correct", "correct"] }];
  assert.equal(buildShareText(3, g, true), "Parlache del día #3 2/6\n⬛🟨⬛⬛⬛\n🟩🟩🟩🟩🟩");
  assert.ok(buildShareText(3, g, false).startsWith("Parlache del día #3 X/6"));
});

test("formatCountdown", () => {
  assert.equal(formatCountdown(0), "00:00:00");
  assert.equal(formatCountdown(3661), "01:01:01");
  assert.equal(formatCountdown(-5), "00:00:00");
});

test("bogotaDate usa UTC−5", () => {
  assert.equal(bogotaDate(new Date("2026-11-27T04:59:59Z")), "2026-11-26");
  assert.equal(bogotaDate(new Date("2026-11-27T05:00:00Z")), "2026-11-27");
});
