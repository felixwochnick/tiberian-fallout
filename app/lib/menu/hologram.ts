import * as THREE from 'three'

/**
 * Green hologram of the main menu as a screen pass.
 *
 * Every pixel is projected onto the plane of the machine and the shapes are
 * evaluated there as distance fields (in Blender's XY coordinates). Like in
 * the original the fill tints the picture instead of covering it, so the
 * brass texture stays visible, and all shapes get thin bright outlines.
 */
export const HologramShader = {
  uniforms: {
    tDiffuse: { value: null as THREE.Texture | null },
    intensity: { value: 0 },
    time: { value: 0 },
    planeY: { value: 0.03 },
    cameraPos: { value: new THREE.Vector3() },
    cameraWorld: { value: new THREE.Matrix4() },
    projectionInverse: { value: new THREE.Matrix4() },
  },
  vertexShader: /* glsl */ `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }`,
  fragmentShader: /* glsl */ `
    uniform sampler2D tDiffuse;
    uniform float intensity;
    uniform float time;
    uniform float planeY;
    uniform vec3 cameraPos;
    uniform mat4 cameraWorld;
    uniform mat4 projectionInverse;
    varying vec2 vUv;

    const float PI = 3.14159265;
    const vec2 KNOB = vec2(-0.8806, -0.6166); // 215° on r = 1.075

    float angleOf(vec2 p) {
      float a = degrees(atan(p.y, p.x));
      return a < 0.0 ? a + 360.0 : a;
    }

    // Signed distance (approx.) to an annular sector, angles in degrees, a1 may exceed 360
    float sector(float r, float a, float r0, float r1, float a0, float a1) {
      float aa = a < a0 ? a + 360.0 : a;
      float da = aa > a1 ? min(aa - a1, a0 + 360.0 - aa) : -min(aa - a0, a1 - aa);
      return max(max(r0 - r, r - r1), da * PI / 180.0 * r);
    }

    void main() {
      vec4 base = texture2D(tDiffuse, vUv);

      // Ray through this pixel onto the plane y = planeY (glTF space)
      vec4 view = projectionInverse * vec4(vUv * 2.0 - 1.0, 1.0, 1.0);
      vec3 dir = normalize((cameraWorld * vec4(view.xyz / view.w, 0.0)).xyz);
      float t = (planeY - cameraPos.y) / dir.y;
      vec2 p = (cameraPos + dir * t).xz * vec2(1.0, -1.0); // back to Blender XY
      float r = length(p);
      float a = angleOf(p);

      float w = max(fwidth(p.x), fwidth(p.y));
      #define INSIDE(d) (1.0 - smoothstep(-w * 0.5, w * 0.5, d))
      #define LINE(d, width) (1.0 - smoothstep(width * 0.5, width * 0.5 + w, abs(d)))
      float lw = max(0.006, w * 1.6);

      float fill = 0.0;
      float edge = 0.0;

      // Outer band: two filled parts, two parts with outline only, a gap under the logo
      float d1 = sector(r, a, 1.02, 1.2, 95.0, 178.0);
      float d2 = sector(r, a, 1.02, 1.2, 208.0, 380.0);
      float d3 = sector(r, a, 1.02, 1.2, 178.0, 208.0);
      float d4 = sector(r, a, 1.02, 1.2, 20.0, 75.0);
      fill += INSIDE(d1) + INSIDE(d2);
      edge += LINE(d1, lw) + LINE(d2, lw) + LINE(d3, lw) + LINE(d4, lw);
      float cyan = INSIDE(sector(r, a, 1.03, 1.19, 44.0, 58.0));

      // Inner band and the thin full circle
      float d5 = sector(r, a, 0.86, 1.02, 100.0, 175.0);
      fill += INSIDE(d5) * 0.85;
      edge += LINE(d5, lw) + LINE(r - 0.86, lw);

      // Centre plate: disc minus the two crescent bites, darker ring around the boss
      float bites = min(length(p - vec2(0.475)) - 0.475, length(p + vec2(0.475)) - 0.475);
      float centre = max(r - 0.5, -bites);
      fill += INSIDE(centre);
      edge += LINE(centre, lw);
      float boss = abs(r - 0.0725) - 0.0175;
      fill -= INSIDE(boss) * 0.55;
      edge += LINE(boss, lw) * 0.7;

      // Knob with a dotted rim
      vec2 k = p - KNOB;
      float knob = length(k) - 0.16;
      fill += INSIDE(knob);
      edge += LINE(knob, lw) * step(0.45, fract(angleOf(k) / 9.0));

      // The cross turns into two glowing beams
      float beam = LINE(p.y, 0.022) + LINE(p.x, 0.022);

      fill = clamp(fill, 0.0, 1.0);
      edge = clamp(edge, 0.0, 1.0);
      beam = clamp(beam, 0.0, 1.0);

      // Slight flicker of the projection
      float k0 = intensity * (0.97 + 0.03 * sin(time * 47.0 + p.y * 30.0));
      float l = dot(base.rgb, vec3(0.2126, 0.7152, 0.0722));
      vec3 green = vec3(0.035, 0.9, 0.2);
      vec3 tinted = base.rgb * 0.12 + green * (0.1 + 1.9 * l);
      vec3 color = mix(base.rgb, tinted, fill * k0 * 0.92);
      color += vec3(0.05, 1.0, 0.22) * edge * k0 * 0.75;
      color = mix(color, vec3(0.04, 1.0, 0.85) * (0.3 + 1.8 * l), cyan * k0 * 0.92);
      color += vec3(0.04, 0.9, 0.18) * beam * k0 * 0.75;
      gl_FragColor = vec4(color, base.a);
    }`,
}
