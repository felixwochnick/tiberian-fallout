<script setup lang="ts">
const { importing, progress, error, importFiles } = useGameAssets()

const dragging = ref(false)
const folderInput = ref<HTMLInputElement>()
const fileInput = ref<HTMLInputElement>()

const percent = computed(() =>
  progress.value && progress.value.total ? Math.round((progress.value.done / progress.value.total) * 100) : 0,
)

function onPick(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files?.length) importFiles([...input.files])
  input.value = ''
}

async function readEntry(entry: FileSystemEntry): Promise<File[]> {
  if (entry.isFile) {
    return new Promise((resolve, reject) => (entry as FileSystemFileEntry).file(f => resolve([f]), reject))
  }
  const reader = (entry as FileSystemDirectoryEntry).createReader()
  const children: FileSystemEntry[] = []
  // readEntries returns results in batches until it yields an empty array
  for (;;) {
    const batch = await new Promise<FileSystemEntry[]>((resolve, reject) => reader.readEntries(resolve, reject))
    if (!batch.length) break
    children.push(...batch)
  }
  return (await Promise.all(children.map(readEntry))).flat()
}

async function onDrop(event: DragEvent) {
  dragging.value = false
  const items = [...(event.dataTransfer?.items ?? [])]
  const entries = items.map(item => item.webkitGetAsEntry?.()).filter((e): e is FileSystemEntry => !!e)
  const files = entries.length
    ? (await Promise.all(entries.map(readEntry))).flat()
    : [...(event.dataTransfer?.files ?? [])]
  if (files.length) importFiles(files)
}

function formatMB(bytes: number) {
  return `${(bytes / 1024 / 1024).toFixed(0)} MB`
}
</script>

<template>
  <div
    class="dropzone"
    :class="{ dragging, busy: importing }"
    @dragover.prevent="dragging = true"
    @dragleave.prevent="dragging = false"
    @drop.prevent="onDrop"
  >
    <template v-if="importing && progress && !progress.disc">
      <p class="dz-title">
        Importiere {{ progress.file }} …
      </p>
      <div class="bar" role="progressbar" :aria-valuenow="percent" aria-valuemin="0" aria-valuemax="100">
        <div class="bar-fill" :style="{ width: `${percent}%` }" />
      </div>
      <p class="hint">
        {{ formatMB(progress.done) }} / {{ formatMB(progress.total) }} ({{ percent }} %)
      </p>
    </template>
    <template v-else>
      <p class="dz-title">
        Installationsordner, MIX-Dateien oder CD-Images (ISO) hierher ziehen
      </p>
      <div class="actions">
        <button class="btn" :disabled="importing" @click="folderInput?.click()">
          Ordner wählen
        </button>
        <button class="btn btn-secondary" :disabled="importing" @click="fileInput?.click()">
          Dateien wählen
        </button>
      </div>
      <p class="hint">
        Die Dateien bleiben in deinem Browser und werden nirgendwohin hochgeladen.
      </p>
    </template>

    <input ref="folderInput" type="file" webkitdirectory hidden @change="onPick">
    <input ref="fileInput" type="file" multiple accept=".mix,.iso,.ini" hidden @change="onPick">
  </div>
  <p v-if="error" class="error" role="alert">
    {{ error }}
  </p>
</template>

<style scoped>
.dropzone {
  border: 2px dashed var(--line);
  border-radius: 6px;
  padding: 28px 20px;
  text-align: center;
  transition: border-color 0.15s, background 0.15s;
}
.dropzone.dragging {
  border-color: var(--tib);
  background: rgba(61, 255, 110, 0.06);
}
.dz-title {
  margin: 0 0 16px;
  font-weight: 600;
}
.actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
}
.hint {
  margin: 14px 0 0;
  font-size: 0.85rem;
  color: var(--muted);
}
.bar {
  height: 10px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 5px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #1fa846, var(--tib));
  transition: width 0.2s;
}
.error {
  color: var(--danger);
  margin: 12px 0 0;
}
</style>
