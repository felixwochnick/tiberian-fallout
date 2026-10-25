<script setup lang="ts">
/**
 * Dialog of the main menu: a translucent sheet that unrolls like a scroll
 * between two chrome pillars (and rolls up again when it closes).
 */
defineProps<{ open: boolean }>()
</script>

<template>
  <Transition name="scroll" :duration="500">
    <section v-if="open" class="scroll" @click.stop>
      <div class="sheet">
        <slot />
      </div>
      <div v-for="side in ['left', 'right']" :key="side" class="pillar" :class="side" aria-hidden="true">
        <i class="cap top" />
        <i class="rod" />
        <i class="cap bottom" />
      </div>
    </section>
  </Transition>
</template>

<style scoped>
.scroll {
  --pillar: 2.1cqw;
  --duration: 0.5s;
  position: absolute;
  left: 22.5%;
  top: 37%;
  width: 55%;
  height: 57%;
  cursor: default;
}
.sheet {
  position: absolute;
  inset: 1.2cqh calc(var(--pillar) * 0.45);
  padding: 2.2cqh 6%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 1.5cqh;
  font: 700 3.1cqh var(--menu);
  color: #c9f25a;
  background:
    /* the sheet curls into the pillars */
    linear-gradient(90deg, rgba(0, 0, 0, 0.45), transparent 4%, transparent 96%, rgba(0, 0, 0, 0.45)),
    linear-gradient(rgba(70, 140, 160, 0.55), rgba(25, 75, 95, 0.62));
  border-top: 1px solid rgba(170, 230, 240, 0.55);
  border-bottom: 1px solid rgba(170, 230, 240, 0.35);
  backdrop-filter: blur(1.5px);
}

/* ---- chrome pillars ---- */
.pillar {
  position: absolute;
  top: 0;
  bottom: 0;
  width: var(--pillar);
  display: flex;
  flex-direction: column;
  align-items: center;
  filter: drop-shadow(0.25cqw 0.3cqh 0.35cqw rgba(0, 0, 0, 0.75));
}
.pillar.left {
  left: calc(var(--pillar) / -2);
}
.pillar.right {
  right: calc(var(--pillar) / -2);
}
.rod {
  flex: 1;
  width: 72%;
  background:
    /* collars below the caps and a groove in the middle */
    linear-gradient(
      transparent 0 3%,
      rgba(0, 0, 0, 0.55) 3% 3.6%,
      rgba(255, 255, 255, 0.5) 3.6% 4.2%,
      transparent 4.2% 49.4%,
      rgba(0, 0, 0, 0.5) 49.4% 50%,
      rgba(255, 255, 255, 0.45) 50% 50.6%,
      transparent 50.6% 95.8%,
      rgba(255, 255, 255, 0.5) 95.8% 96.4%,
      rgba(0, 0, 0, 0.55) 96.4% 97%,
      transparent 97%
    ),
    /* fine machining marks */
    repeating-linear-gradient(transparent 0 2px, rgba(0, 0, 0, 0.05) 2px 3px),
    /* round chrome body with a sharp highlight */
    linear-gradient(90deg,
      #2b2e31 0%,
      #6f7479 10%,
      #c8ccd0 26%,
      #ffffff 36%,
      #e3e6e9 42%,
      #9a9fa4 58%,
      #5b6065 76%,
      #a6abb0 88%,
      #3a3d40 100%);
}
.cap {
  position: relative;
  width: 100%;
  height: 4.4cqh;
  border-radius: 0.3cqw;
  background:
    linear-gradient(rgba(255, 255, 255, 0.35), transparent 30%, transparent 70%, rgba(0, 0, 0, 0.45)),
    linear-gradient(90deg, #26282b 0%, #74797e 14%, #d5d9dd 32%, #f6f7f8 40%, #a3a8ad 60%, #55595e 82%, #2c2f32 100%);
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.6);
}
/* screw head with a slot */
.cap::before {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  width: 1.15cqw;
  aspect-ratio: 1;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  background:
    linear-gradient(135deg, transparent 44%, #1d1f21 44% 56%, transparent 56%),
    radial-gradient(circle at 35% 30%, #ffffff, #b9bdc1 40%, #5d6166 75%, #2a2c2e);
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.7), 0 1px 1px rgba(255, 255, 255, 0.4);
}
/* small ring between cap and rod */
.cap::after {
  content: '';
  position: absolute;
  left: 8%;
  right: 8%;
  height: 0.6cqh;
  background: linear-gradient(90deg, #2a2c2e, #b7bbbf 35%, #f2f3f4 45%, #6c7075 80%, #2a2c2e);
}
.cap.top::after {
  top: 100%;
}
.cap.bottom::after {
  bottom: 100%;
}

/* ---- unroll / roll up ---- */
.scroll-enter-active .sheet,
.scroll-leave-active .sheet {
  animation: unroll var(--duration) cubic-bezier(0.3, 0.1, 0.25, 1) both;
}
.scroll-enter-active .pillar.left,
.scroll-leave-active .pillar.left {
  animation: pillar-left var(--duration) cubic-bezier(0.3, 0.1, 0.25, 1) both;
}
.scroll-enter-active .pillar.right,
.scroll-leave-active .pillar.right {
  animation: pillar-right var(--duration) cubic-bezier(0.3, 0.1, 0.25, 1) both;
}
.scroll-leave-active .sheet,
.scroll-leave-active .pillar {
  animation-direction: reverse !important;
}
@keyframes unroll {
  0%,
  12% {
    clip-path: inset(0 50% 0 50%);
  }
  100% {
    clip-path: inset(0 0 0 0);
  }
}
/* both pillars start together in the middle (half the width of the 55 % dialog) */
@keyframes pillar-left {
  0% {
    transform: translateX(27.5cqw) scaleY(0.2);
    opacity: 0;
  }
  12% {
    transform: translateX(27.5cqw) scaleY(1);
    opacity: 1;
  }
  100% {
    transform: none;
  }
}
@keyframes pillar-right {
  0% {
    transform: translateX(-27.5cqw) scaleY(0.2);
    opacity: 0;
  }
  12% {
    transform: translateX(-27.5cqw) scaleY(1);
    opacity: 1;
  }
  100% {
    transform: none;
  }
}
</style>
