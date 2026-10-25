<script setup lang="ts">
/**
 * First screen when the game starts: what it is made with and where the project lives.
 * Fades in and out by itself; a click or Esc / Space / Enter skips it (the link opens
 * the project in a new tab without skipping).
 */
const emit = defineEmits<{ done: [] }>()

const PROJECT_URL = 'https://github.com/felixwochnick/tiberian-fallout'
/** Seconds: fade in, hold, fade out */
const TIMING = { in: 0.8, hold: 3.6, out: 0.8 }

const leaving = ref(false)
let timer: ReturnType<typeof setTimeout> | undefined

function finish() {
  if (leaving.value) return
  leaving.value = true
  clearTimeout(timer)
  timer = setTimeout(() => emit('done'), TIMING.out * 1000)
}

function onKey(event: KeyboardEvent) {
  if (event.key === 'Escape' || event.key === ' ' || event.key === 'Enter') finish()
}

onMounted(() => {
  window.addEventListener('keydown', onKey)
  timer = setTimeout(finish, (TIMING.in + TIMING.hold) * 1000)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  clearTimeout(timer)
})
</script>

<template>
  <div class="splash" :class="{ leaving }" :style="{ '--in': `${TIMING.in}s`, '--out': `${TIMING.out}s` }" @click="finish">
    <div class="content">
      <p class="title">
        Command &amp; Conquer<br><span>Tiberian Fallout</span>
      </p>
      <p class="made">
        Entwickelt mit
      </p>
      <!-- the logos: Simple Icons (simpleicons.org, CC0) -->
      <ul class="tools">
        <li>
          <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="2" y="2" width="20" height="20" fill="#fff" /><path fill="#3178c6" d="M1.125 0C.502 0 0 .502 0 1.125v21.75C0 23.498.502 24 1.125 24h21.75c.623 0 1.125-.502 1.125-1.125V1.125C24 .502 23.498 0 22.875 0zm17.363 9.75c.612 0 1.154.037 1.627.111a6.38 6.38 0 0 1 1.306.34v2.458a3.95 3.95 0 0 0-.643-.361 5.093 5.093 0 0 0-.717-.26 5.453 5.453 0 0 0-1.426-.2c-.3 0-.573.028-.819.086a2.1 2.1 0 0 0-.623.242c-.17.104-.3.229-.393.374a.888.888 0 0 0-.14.49c0 .196.053.373.156.529.104.156.252.304.443.444s.423.276.696.41c.273.135.582.274.926.416.47.197.892.407 1.266.628.374.222.695.473.963.753.268.279.472.598.614.957.142.359.214.776.214 1.253 0 .657-.125 1.21-.373 1.656a3.033 3.033 0 0 1-1.012 1.085 4.38 4.38 0 0 1-1.487.596c-.566.12-1.163.18-1.79.18a9.916 9.916 0 0 1-1.84-.164 5.544 5.544 0 0 1-1.512-.493v-2.63a5.033 5.033 0 0 0 3.237 1.2c.333 0 .624-.03.872-.09.249-.06.456-.144.623-.25.166-.108.29-.234.373-.38a1.023 1.023 0 0 0-.074-1.089 2.12 2.12 0 0 0-.537-.5 5.597 5.597 0 0 0-.807-.444 27.72 27.72 0 0 0-1.007-.436c-.918-.383-1.602-.852-2.053-1.405-.45-.553-.676-1.222-.676-2.005 0-.614.123-1.141.369-1.582.246-.441.58-.804 1.004-1.089a4.494 4.494 0 0 1 1.47-.629 7.536 7.536 0 0 1 1.77-.201zm-15.113.188h9.563v2.166H9.506v9.646H6.789v-9.646H3.375z" /></svg>
          TypeScript
        </li>
        <li>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#fff" d="M.38 0a.268.268 0 0 0-.256.332l2.894 11.716a.268.268 0 0 0 .01.04l2.89 11.708a.268.268 0 0 0 .447.128L23.802 7.15a.268.268 0 0 0-.112-.45l-5.784-1.667a.268.268 0 0 0-.123-.035L6.38 1.715a.268.268 0 0 0-.144-.04L.456.01A.268.268 0 0 0 .38 0zm.374.654L5.71 2.08 1.99 5.664zM6.61 2.34l4.864 1.4-3.65 3.515zm-.522.12l1.217 4.926-4.877-1.4zm6.28 1.538l4.878 1.404-3.662 3.53zm-.52.13l1.208 4.9-4.853-1.392zm6.3 1.534l4.947 1.424-3.715 3.574zm-.524.12l1.215 4.926-4.876-1.398zm-15.432.696l4.964 1.424-3.726 3.586zM8.047 8.15l4.877 1.4-3.66 3.527zm-.518.137l1.236 5.017-4.963-1.432zm6.274 1.535l4.965 1.425-3.73 3.586zm-.52.127l1.235 5.012-4.958-1.43zm-9.63 2.438l4.873 1.406-3.656 3.523zm5.854 1.687l4.863 1.403-3.648 3.51zm-.54.04l1.214 4.927-4.875-1.4zm-3.896 4.02l5.037 1.442-3.782 3.638z" /></svg>
          Three.js
        </li>
        <li>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#d97757" d="m4.7144 15.9555 4.7174-2.6471.079-.2307-.079-.1275h-.2307l-.7893-.0486-2.6956-.0729-2.3375-.0971-2.2646-.1214-.5707-.1215-.5343-.7042.0546-.3522.4797-.3218.686.0608 1.5179.1032 2.2767.1578 1.6514.0972 2.4468.255h.3886l.0546-.1579-.1336-.0971-.1032-.0972L6.973 9.8356l-2.55-1.6879-1.3356-.9714-.7225-.4918-.3643-.4614-.1578-1.0078.6557-.7225.8803.0607.2246.0607.8925.686 1.9064 1.4754 2.4893 1.8336.3643.3035.1457-.1032.0182-.0728-.164-.2733-1.3539-2.4467-1.445-2.4893-.6435-1.032-.17-.6194c-.0607-.255-.1032-.4674-.1032-.7285L6.287.1335 6.6997 0l.9957.1336.419.3642.6192 1.4147 1.0018 2.2282 1.5543 3.0296.4553.8985.2429.8318.091.255h.1579v-.1457l.1275-1.706.2368-2.0947.2307-2.6957.0789-.7589.3764-.9107.7468-.4918.5828.2793.4797.686-.0668.4433-.2853 1.8517-.5586 2.9021-.3643 1.9429h.2125l.2429-.2429.9835-1.3053 1.6514-2.0643.7286-.8196.85-.9046.5464-.4311h1.0321l.759 1.1293-.34 1.1657-1.0625 1.3478-.8804 1.1414-1.2628 1.7-.7893 1.36.0729.1093.1882-.0183 2.8535-.607 1.5421-.2794 1.8396-.3157.8318.3886.091.3946-.3278.8075-1.967.4857-2.3072.4614-3.4364.8136-.0425.0304.0486.0607 1.5482.1457.6618.0364h1.621l3.0175.2247.7892.522.4736.6376-.079.4857-1.2142.6193-1.6393-.3886-3.825-.9107-1.3113-.3279h-.1822v.1093l1.0929 1.0686 2.0035 1.8092 2.5075 2.3314.1275.5768-.3218.4554-.34-.0486-2.2039-1.6575-.85-.7468-1.9246-1.621h-.1275v.17l.4432.6496 2.3436 3.5214.1214 1.0807-.17.3521-.6071.2125-.6679-.1214-1.3721-1.9246L14.38 17.959l-1.1414-1.9428-.1397.079-.674 7.2552-.3156.3703-.7286.2793-.6071-.4614-.3218-.7468.3218-1.4753.3886-1.9246.3157-1.53.2853-1.9004.17-.6314-.0121-.0425-.1397.0182-1.4328 1.9672-2.1796 2.9446-1.7243 1.8456-.4128.164-.7164-.3704.0667-.6618.4008-.5889 2.386-3.0357 1.4389-1.882.929-1.0868-.0062-.1579h-.0546l-6.3385 4.1164-1.1293.1457-.4857-.4554.0608-.7467.2307-.2429 1.9064-1.3114Z" /></svg>
          Claude
        </li>
      </ul>
      <a class="project" :href="PROJECT_URL" target="_blank" rel="noopener" @click.stop>
        <svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 .5a11.5 11.5 0 0 0-3.64 22.4c.58.1.79-.25.79-.56v-2c-3.2.7-3.88-1.37-3.88-1.37-.53-1.33-1.28-1.69-1.28-1.69-1.05-.71.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.71 1.26 3.37.96.1-.75.4-1.26.73-1.55-2.56-.29-5.25-1.28-5.25-5.68 0-1.26.45-2.28 1.19-3.09-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.77 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.81 1.19 1.83 1.19 3.09 0 4.41-2.7 5.38-5.27 5.67.41.36.78 1.06.78 2.13v3.16c0 .31.21.67.8.56A11.5 11.5 0 0 0 12 .5z" /></svg>
        github.com/felixwochnick/tiberian-fallout
      </a>
      <p class="note">
        Inoffizielles Fanprojekt · Command &amp; Conquer ist eine Marke von Electronic Arts
      </p>
    </div>
  </div>
</template>

<style scoped>
.splash {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: grid;
  place-items: center;
  padding: 16px;
  background: radial-gradient(ellipse at 50% 45%, #0d1a10, #000 70%);
  cursor: pointer;
  user-select: none;
  animation: fade-in var(--in) ease-out both;
}
.splash.leaving {
  animation: fade-out var(--out) ease-in both;
}
@keyframes fade-in {
  from {
    opacity: 0;
  }
}
@keyframes fade-out {
  to {
    opacity: 0;
  }
}
.content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: clamp(10px, 2.2vh, 24px);
  text-align: center;
}
.title {
  margin: 0;
  font: 800 clamp(18px, 2.6vw, 34px) / 1.1 var(--display);
  text-transform: uppercase;
  color: #e9e3c4;
}
.title span {
  color: var(--tib);
  text-shadow: 0 0 24px rgba(61, 255, 110, 0.35);
}
.made {
  margin: clamp(8px, 2vh, 20px) 0 0;
  font: 600 clamp(13px, 1.2vw, 17px) var(--body);
  letter-spacing: 0.3em;
  text-transform: uppercase;
  color: var(--muted);
}
.tools {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: clamp(14px, 3vw, 40px);
  margin: 0;
  padding: 0;
  list-style: none;
}
.tools li {
  display: flex;
  align-items: center;
  gap: 0.5em;
  font: 700 clamp(16px, 1.8vw, 26px) var(--body);
  color: #fff;
}
.tools svg {
  width: 1.3em;
  height: 1.3em;
}
.project {
  display: inline-flex;
  align-items: center;
  gap: 0.5em;
  margin-top: clamp(8px, 2vh, 20px);
  padding: 8px 16px;
  border: 1px solid var(--line);
  border-radius: 6px;
  color: var(--tib);
  font: 600 clamp(13px, 1.1vw, 16px) var(--body);
  text-decoration: none;
}
.project svg {
  width: 1.2em;
  height: 1.2em;
}
.project:hover,
.project[data-hover] {
  border-color: var(--tib);
  background: rgba(61, 255, 110, 0.08);
}
.note {
  margin: 0;
  font: 400 clamp(11px, 0.9vw, 13px) var(--body);
  color: var(--muted);
}
</style>
