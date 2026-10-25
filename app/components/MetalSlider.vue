<script setup lang="ts">
/** Slider of the menu dialogs: recessed groove with ticks, lit fill and a chrome grip. */
const props = withDefaults(defineProps<{
  label: string
  min?: number
  max?: number
  step?: number
  /** Text shown on the right, defaults to the value */
  display?: string
}>(), { min: 0, max: 100, step: 1, display: undefined })

const value = defineModel<number>({ required: true })
const emit = defineEmits<{ change: [] }>()

const fill = computed(() => `${((value.value - props.min) / (props.max - props.min)) * 100}%`)
const ticks = computed(() => Math.min(20, Math.round((props.max - props.min) / props.step)))
</script>

<template>
  <label class="slider">
    <span class="row">
      <span>{{ label }}</span>
      <span>{{ display ?? value }}</span>
    </span>
    <span class="control" :style="{ '--fill': fill, '--ticks': ticks }">
      <input
        v-model.number="value"
        type="range"
        :min="min"
        :max="max"
        :step="step"
        @change="emit('change')"
      >
    </span>
  </label>
</template>

<style scoped>
.slider {
  display: flex;
  flex-direction: column;
  gap: 0.5cqh;
}
.row {
  display: flex;
  justify-content: space-between;
}
.control {
  position: relative;
  display: block;
  height: 3.8cqh;
}
/* groove */
.control::before {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: 50%;
  height: 1.5cqh;
  transform: translateY(-50%);
  border-radius: 0.3cqh;
  background:
    /* lit part left of the grip */
    linear-gradient(90deg, rgba(150, 230, 60, 0.85), rgba(201, 242, 90, 0.95)) 0 0 / var(--fill) 100% no-repeat,
    linear-gradient(#04141b, #0d2d38);
  box-shadow:
    inset 0 0.25cqh 0.4cqh rgba(0, 0, 0, 0.9),
    0 1px 0 rgba(170, 230, 240, 0.35);
  border: 1px solid #02090c;
}
/* tick marks below the groove */
.control::after {
  content: '';
  position: absolute;
  left: 1.1cqh;
  right: 1.1cqh;
  bottom: 0;
  height: 0.6cqh;
  background: repeating-linear-gradient(90deg, rgba(201, 242, 90, 0.6) 0 1px, transparent 1px calc(100% / var(--ticks)));
  pointer-events: none;
}
input {
  position: relative;
  z-index: 1;
  width: 100%;
  height: 100%;
  margin: 0;
  background: transparent;
  appearance: none;
  -webkit-appearance: none;
  cursor: pointer;
}
input:focus-visible {
  outline: 1px dashed rgba(201, 242, 90, 0.7);
  outline-offset: 2px;
}
input::-webkit-slider-runnable-track {
  height: 100%;
  background: transparent;
}
input::-moz-range-track {
  height: 100%;
  background: transparent;
}
/* chrome grip with ridges */
input::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 2.2cqh;
  height: 3.8cqh;
  border: 1px solid #1a1c1e;
  border-radius: 0.25cqh;
  background:
    repeating-linear-gradient(transparent 0 0.45cqh, rgba(0, 0, 0, 0.45) 0.45cqh 0.6cqh, rgba(255, 255, 255, 0.5) 0.6cqh 0.75cqh) 50% 50% / 60% 55% no-repeat,
    linear-gradient(90deg, #4c5055, #d9dce0 30%, #ffffff 42%, #9ca1a6 70%, #3e4246);
  box-shadow: 0 0.2cqh 0.4cqh rgba(0, 0, 0, 0.8);
}
input::-moz-range-thumb {
  width: 2.2cqh;
  height: 3.8cqh;
  border: 1px solid #1a1c1e;
  border-radius: 0.25cqh;
  background:
    repeating-linear-gradient(transparent 0 0.45cqh, rgba(0, 0, 0, 0.45) 0.45cqh 0.6cqh, rgba(255, 255, 255, 0.5) 0.6cqh 0.75cqh) 50% 50% / 60% 55% no-repeat,
    linear-gradient(90deg, #4c5055, #d9dce0 30%, #ffffff 42%, #9ca1a6 70%, #3e4246);
  box-shadow: 0 0.2cqh 0.4cqh rgba(0, 0, 0, 0.8);
}
input[data-hover]::-webkit-slider-thumb {
  filter: brightness(1.12);
}
</style>
