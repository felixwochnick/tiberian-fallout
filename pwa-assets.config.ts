import { defineConfig, minimal2023Preset } from '@vite-pwa/assets-generator/config'

// App icons for the PWA from public/icon.svg: `pnpm generate-pwa-assets`
export default defineConfig({
  headLinkOptions: { preset: '2023' },
  preset: {
    ...minimal2023Preset,
    // dark ground like the icon, so the maskable and Apple icons have no white edge
    maskable: { ...minimal2023Preset.maskable, resizeOptions: { background: '#020604' } },
    apple: { ...minimal2023Preset.apple, resizeOptions: { background: '#020604' } },
  },
  images: ['public/icon.svg'],
})
