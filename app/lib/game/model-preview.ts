import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { applyHouseColour } from './models'

/**
 * Small turning previews of the 3D models, all drawn by one WebGL renderer (browsers
 * allow only a few WebGL contexts at once) and copied into each preview's 2D canvas.
 * The models stand in the game's light and are seen from the game's angle.
 */

/** Default size of a preview in pixels */
const SIZE = 160

interface Preview {
  canvas: HTMLCanvasElement
  /** Size in pixels (square) */
  size: number
  scene: THREE.Scene
  camera: THREE.PerspectiveCamera
  model: THREE.Object3D
  mixer?: THREE.AnimationMixer
}

let renderer: THREE.WebGLRenderer | undefined
const previews = new Set<Preview>()
let running = false
let last = 0

function loop(now: number) {
  if (!previews.size || !renderer) {
    running = false
    return
  }
  const seconds = Math.min(0.1, (now - last) / 1000)
  last = now
  for (const preview of previews) {
    preview.model.rotation.y += seconds * 0.6
    preview.mixer?.update(seconds)
    if (renderer.domElement.width !== preview.size) renderer.setSize(preview.size, preview.size, false)
    renderer.render(preview.scene, preview.camera)
    const ctx = preview.canvas.getContext('2d')!
    ctx.clearRect(0, 0, preview.size, preview.size)
    ctx.drawImage(renderer.domElement, 0, 0)
  }
  requestAnimationFrame(loop)
}

/** Shows the model from `url` turning in `canvas` (`size` pixels square); returns a function that stops it. */
export async function previewModel(canvas: HTMLCanvasElement, url: string, houseColour = 0xd8b43a, size = SIZE) {
  renderer ??= new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true })
  renderer.outputColorSpace = THREE.SRGBColorSpace
  canvas.width = size
  canvas.height = size

  const gltf = await new GLTFLoader().loadAsync(url)
  const model = gltf.scene
  model.traverse((node) => {
    const mesh = node as THREE.Mesh
    if (!mesh.isMesh) return
    for (const mat of [mesh.material].flat() as THREE.MeshStandardMaterial[]) {
      applyHouseColour(mat, houseColour)
      if (mat.name.startsWith('Glow')) {
        mat.blending = THREE.AdditiveBlending
        mat.depthWrite = false
      }
    }
  })
  // the finished building / the idle unit / the flying aircraft, not the build-up
  let mixer: THREE.AnimationMixer | undefined
  const idle = gltf.animations.find(clip => clip.name === 'Idle') ?? gltf.animations.find(clip => clip.name === 'Fly')
  const build = gltf.animations.find(clip => clip.name === 'Build')
  if (idle || build) {
    mixer = new THREE.AnimationMixer(model)
    if (build) {
      const action = mixer.clipAction(build)
      action.setLoop(THREE.LoopOnce, 1)
      action.clampWhenFinished = true
      action.play()
      action.time = build.duration
    }
    if (idle) mixer.clipAction(idle).play()
    mixer.update(0)
  }

  // frame the model: centred (aircraft hang high above their origin), seen from the
  // game's angle (30° down)
  const box = new THREE.Box3().setFromObject(model, true)
  const centre = box.getCenter(new THREE.Vector3())
  const radius = box.getSize(new THREE.Vector3()).length() / 2
  const pivot = new THREE.Group()
  model.position.sub(centre)
  pivot.add(model)
  const scene = new THREE.Scene()
  scene.add(pivot)
  const sun = new THREE.DirectionalLight(0xfff4e0, 2.6)
  sun.position.set(-6, 9, -2)
  scene.add(sun, new THREE.HemisphereLight(0xdfe8ff, 0x5a5040, 1.1))
  const camera = new THREE.PerspectiveCamera(30, 1, 0.01, 100)
  const distance = radius / Math.sin(THREE.MathUtils.degToRad(15)) * 1.05
  const elevation = THREE.MathUtils.degToRad(30)
  const lookAt = new THREE.Vector3()
  camera.position.set(0, Math.sin(elevation) * distance, Math.cos(elevation) * distance).add(lookAt)
  camera.lookAt(lookAt)

  const preview: Preview = { canvas, size, scene, camera, model: pivot, mixer }
  previews.add(preview)
  if (!running) {
    running = true
    last = performance.now()
    requestAnimationFrame(loop)
  }
  return () => {
    previews.delete(preview)
    model.traverse((node) => {
      const mesh = node as THREE.Mesh
      if (!mesh.isMesh) return
      mesh.geometry.dispose()
      for (const mat of [mesh.material].flat()) mat.dispose()
    })
  }
}
