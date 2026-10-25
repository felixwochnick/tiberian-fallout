<script setup lang="ts">
/**
 * "Tastenbelegung": the shortcut of every action. Clicking one waits for the new key;
 * a key that is already used swaps with it, Esc cancels. Used in the options of the
 * main menu and of the in-game menu.
 */
const emit = defineEmits<{ click: [] }>()
const settings = useSettings()
/** The action waiting for its new key */
const listening = defineModel<KeyAction | undefined>('listening', { default: undefined })

function listen(action: KeyAction) {
  emit('click')
  listening.value = listening.value === action ? undefined : action
}

/** Takes the next key while listening, before the menus and the game see it */
function onKey(event: KeyboardEvent) {
  const action = listening.value
  if (!action) return
  event.preventDefault()
  event.stopImmediatePropagation()
  listening.value = undefined
  if (event.code === 'Escape' || RESERVED_KEYS.includes(event.code)) return
  const old = settings.keys[action]
  // the action that had this key gets the old one
  const other = (Object.keys(settings.keys) as KeyAction[]).find(a => a !== action && settings.keys[a] === event.code)
  if (other) settings.keys[other] = old
  settings.keys[action] = event.code
  emit('click')
}

function reset() {
  emit('click')
  listening.value = undefined
  Object.assign(settings.keys, DEFAULT_KEYS)
}

onMounted(() => window.addEventListener('keydown', onKey, { capture: true }))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey, { capture: true }))
</script>

<template>
  <ul class="dialog-list keys">
    <li v-for="{ action, label } in KEY_ACTIONS" :key="action">
      <span>{{ label }}</span>
      <button class="key" :class="{ listening: listening === action }" @click="listen(action)">
        {{ listening === action ? 'Taste drücken …' : keyName(settings.keys[action]) }}
      </button>
    </li>
    <li class="fixed">
      <span>Menü öffnen / schließen</span>
      <span class="key">Esc</span>
    </li>
  </ul>
  <p class="keys-hint">
    Klicke auf eine Taste und drücke die neue. Ist sie schon belegt, werden beide getauscht. Esc bricht ab.
  </p>
  <div class="dialog-buttons">
    <button class="metal-btn" @click="reset()">
      Standard
    </button>
    <slot />
  </div>
</template>

<style scoped>
.keys {
  flex: 1 1 auto;
  min-height: 0;
  font-size: 2.5cqh;
}
.keys li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1em;
  cursor: default;
}
.keys li[data-hover] {
  background: none;
}
.key {
  min-width: 5.5em;
  padding: 0.1em 0.6em;
  border: 1px solid rgba(170, 230, 240, 0.6);
  background: rgba(10, 30, 40, 0.6);
  color: #ffe85a;
  font: inherit;
  text-align: center;
  cursor: pointer;
}
.key[data-hover] {
  background: rgba(130, 200, 220, 0.35);
}
.key.listening {
  color: #fff;
  animation: listening 0.8s steps(2) infinite;
}
@keyframes listening {
  50% {
    background: rgba(130, 200, 220, 0.45);
  }
}
.fixed .key {
  color: #9fd0dc;
  cursor: default;
}
.keys-hint {
  margin: 0;
  font: 600 2cqh / 1.35 var(--body);
  color: #9fd0dc;
}
</style>
