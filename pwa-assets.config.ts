import { defineConfig, minimal2023Preset } from '@vite-pwa/assets-generator/config'

// App icons for the PWA from public/icon.svg: `pnpm generate-pwa-assets`
export default defineConfig({
  headLinkOptions: { preset: '2023' },
  preset: {
    ...minimal2023Preset,
    // the system rounds these itself: full size on the icon's own dark ground, so its
    // rounded corners disappear into it (the emblem stays inside the maskable safe zone)
    maskable: { ...minimal2023Preset.maskable, padding: 0, resizeOptions: { background: '#020604' } },
    apple: { ...minimal2023Preset.apple, padding: 0, resizeOptions: { background: '#020604' } },
  },
  images: ['public/icon.svg'],
})
