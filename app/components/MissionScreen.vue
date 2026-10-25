<script setup lang="ts">
import type { Mission } from '~/lib/game/campaigns'

/**
 * Briefing before a campaign mission and the result after it, on the unrolling scroll
 * of the menus. The briefing text is typed out like a transmission.
 */
const props = defineProps<{
  mission: Mission
  /** undefined: briefing; otherwise the mission's end */
  result?: 'won' | 'lost'
}>()
const emit = defineEmits<{ start: [], retry: [], leave: [] }>()

const sounds = useUiSounds()
const typed = ref(0)
const text = computed(() => props.mission.briefing.join('\n\n'))
let timer: ReturnType<typeof setInterval> | undefined

onMounted(() => {
  if (props.result) {
    sounds.speak(props.result === 'won' ? 'evaMissionAccomplished' : 'evaMissionFailed')
    return
  }
  timer = setInterval(() => {
    typed.value = Math.min(text.value.length, typed.value + 2)
    if (typed.value >= text.value.length) clearInterval(timer)
  }, 30)
})
onBeforeUnmount(() => clearInterval(timer))

function click(action: () => void) {
  sounds.play('click')
  action()
}

function start() {
  // a click while typing shows the whole text first
  if (typed.value < text.value.length) {
    typed.value = text.value.length
    clearInterval(timer)
    return
  }
  emit('start')
}
</script>

<template>
  <div class="mission">
    <div class="frame">
      <MenuScroll :open="true" class="sheet-pos">
        <template v-if="!result">
          <h2 class="dialog-title">
            {{ mission.title }}
          </h2>
          <p class="briefing">
            {{ text.slice(0, typed) }}<span v-if="typed < text.length" class="caret">▌</span>
          </p>
          <ul class="dialog-list objectives">
            <li v-for="objective in mission.objectives" :key="objective">
              {{ objective }}
            </li>
          </ul>
          <div class="dialog-buttons">
            <button class="metal-btn" @click="click(start)">
              {{ typed < text.length ? 'Überspringen' : 'Mission starten' }}
            </button>
            <button class="metal-btn" @click="click(() => emit('leave'))">
              Hauptmenü
            </button>
          </div>
        </template>
        <template v-else>
          <h2 class="dialog-title result" :class="result">
            {{ result === 'won' ? 'Mission erfüllt' : 'Mission gescheitert' }}
          </h2>
          <p class="briefing">
            {{ result === 'won'
              ? 'Die Angriffe der Bruderschaft wurden zurückgeschlagen. Die Stellung ist sicher. Gut gemacht, Kommandant.'
              : 'Unsere Truppen sind gefallen. Nod hat den Sektor eingenommen.' }}
          </p>
          <div class="dialog-buttons">
            <button class="metal-btn" @click="click(() => emit('retry'))">
              {{ result === 'won' ? 'Nochmal spielen' : 'Neu versuchen' }}
            </button>
            <button class="metal-btn" @click="click(() => emit('leave'))">
              Hauptmenü
            </button>
          </div>
        </template>
      </MenuScroll>
    </div>
  </div>
</template>

<style scoped>
.mission {
  position: fixed;
  inset: 0;
  z-index: 90;
  background: rgba(0, 0, 0, 0.7);
}
.frame {
  position: absolute;
  left: 50%;
  top: 50%;
  width: min(100vw, 160vh);
  aspect-ratio: 16 / 10;
  transform: translate(-50%, -50%);
  container-type: size;
}
.frame .sheet-pos {
  top: 10%;
  height: 80%;
}
.briefing {
  flex: 1;
  min-height: 0;
  margin: 0;
  overflow: auto;
  white-space: pre-line;
  font: 600 2.6cqh / 1.45 var(--body);
  color: #d8f0c0;
}
.caret {
  animation: blink 0.8s steps(2) infinite;
}
@keyframes blink {
  50% {
    opacity: 0;
  }
}
.objectives {
  flex: 0 0 auto;
  font-size: 2.3cqh;
}
.objectives li {
  cursor: default;
}
.objectives li::before {
  content: '▸ ';
  color: #ffe85a;
}
.objectives li[data-hover] {
  background: none;
}
.result.won {
  color: #7cff6a;
}
.result.lost {
  color: #ff6a50;
}
</style>
