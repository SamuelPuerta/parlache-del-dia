// Parallax suave de las montañas. Solo mueve capas con variables CSS (--px, --py).

const reduce = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

export function initScene(scene) {
  if (reduce()) return;
  let tx = 0, ty = 0, cx = 0, cy = 0, raf = 0;

  const loop = () => {
    cx += (tx - cx) * 0.06;
    cy += (ty - cy) * 0.06;
    scene.style.setProperty("--px", cx.toFixed(3));
    scene.style.setProperty("--py", cy.toFixed(3));
    raf = Math.abs(tx - cx) + Math.abs(ty - cy) > 0.002 ? requestAnimationFrame(loop) : 0;
  };
  const kick = () => { if (!raf) raf = requestAnimationFrame(loop); };

  addEventListener("pointermove", (e) => {
    if (e.pointerType === "touch") return;
    tx = (e.clientX / innerWidth - 0.5) * -2;
    ty = (e.clientY / innerHeight - 0.5) * -2;
    kick();
  }, { passive: true });

  addEventListener("deviceorientation", (e) => {
    if (e.gamma == null) return;
    tx = Math.max(-1, Math.min(1, e.gamma / 25)) * -1;
    ty = Math.max(-1, Math.min(1, ((e.beta || 45) - 45) / 25)) * -1;
    kick();
  }, { passive: true });
}

export function setMood(mood) {
  document.body.classList.toggle("mood-won", mood === "won");
  document.body.classList.toggle("mood-lost", mood === "lost");
}
