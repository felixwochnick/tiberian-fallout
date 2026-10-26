import { decodeAud, toAudioBuffer } from '../formats/aud'
import { MixArchive } from '../formats/mix'
import { decodeVqaAudio } from '../formats/vqa'
import { readMovie } from '../game/movies'
import type { AssetStore } from '../storage/asset-store'

async function loadVqaSound(ctx: BaseAudioContext, store: AssetStore, name: string) {
  const bytes = await readMovie(store, name)
  return bytes && toAudioBuffer(ctx, decodeVqaAudio(bytes))
}

/** Sound track of the 6 second startup animation (STARTUP.VQA from MOVIES01.MIX). */
export const loadStartupSound = (ctx: BaseAudioContext, store: AssetStore) => loadVqaSound(ctx, store, 'STARTUP.VQA')

/** Sound track of the 8.7 second Westwood logo (WWLOGO.VQA from MOVIES01.MIX). */
export const loadWestwoodSound = (ctx: BaseAudioContext, store: AssetStore) => loadVqaSound(ctx, store, 'WWLOGO.VQA')

/** The "Intro" theme that plays in the main menu (INTRO.AUD in TIBSUN.MIX → LOCAL.MIX). */
export async function loadMenuMusic(ctx: BaseAudioContext, store: AssetStore) {
  const tibsun = await store.get('TIBSUN.MIX')
  if (!tibsun) return undefined
  const local = await (await MixArchive.open(tibsun, 'TIBSUN.MIX')).openNested('LOCAL.MIX')
  const bytes = await local?.read('INTRO.AUD')
  return bytes && toAudioBuffer(ctx, decodeAud(bytes))
}

/**
 * Interface sounds, addressed by file name or, where the name is not known, by their
 * MIX hash (found by scanning TIBSUN.MIX for short sounds).
 */
const UI_SOUNDS: Record<string, readonly [mix: string | number, file: number | string]> = {
  /** Mechanical slide: a dialog unrolls between its metal pillars (confirmed) */
  open: ['SOUNDS.MIX', 0xd2c3a513],
  /** Click of a menu button: CLICKY1.AUD (confirmed) */
  click: ['SOUNDS.MIX', 0x526404e5],
  /** Radar comes online (RadarOn= in RULES.INI) */
  radarOn: ['SOUNDS.MIX', 'COMMUP1.AUD'],
  /** Radar goes offline (RadarOff= in RULES.INI) */
  radarOff: ['SOUNDS.MIX', 'RADARDN1.AUD'],
  // EVA, the GDI computer voice (SPEECH01.MIX; file names as in OpenRA's Tiberian Sun mod)
  /** "Building" – a structure is started */
  evaBuilding: ['SPEECH01.MIX', '00-I216.AUD'],
  /** "Training" – a unit is started */
  evaTraining: ['SPEECH01.MIX', '00-I062.AUD'],
  /** "Construction complete" */
  evaConstructionComplete: ['SPEECH01.MIX', '00-I018.AUD'],
  /** "Unit ready" */
  evaUnitReady: ['SPEECH01.MIX', '00-I076.AUD'],
  /** "New construction options" – something new can be built */
  evaNewOptions: ['SPEECH01.MIX', '00-I032.AUD'],
  /** "On hold" */
  evaOnHold: ['SPEECH01.MIX', '00-I218.AUD'],
  /** "Cancelled" */
  evaCancelled: ['SPEECH01.MIX', '00-I220.AUD'],
  /** "Insufficient funds" */
  evaInsufficientFunds: ['SPEECH01.MIX', '00-I022.AUD'],
  /** "Cannot deploy here" */
  evaCannotPlace: ['SPEECH01.MIX', '00-I016.AUD'],
  /** "Unable to comply, building in progress" */
  evaBuildingInProgress: ['SPEECH01.MIX', '00-I064.AUD'],
  /** "Establishing battlefield control, stand by" – a mission starts, control comes (back) */
  evaStartGame: ['SPEECH01.MIX', '00-I200.AUD'],
  /** "Our base is under attack" – a building of the player is attacked */
  evaBaseAttack: ['SPEECH01.MIX', '00-I082.AUD'],
  /** "Unit lost" */
  evaUnitLost: ['SPEECH01.MIX', '00-I074.AUD'],
  /** "Harvester under attack" */
  evaHarvesterAttack: ['SPEECH01.MIX', '00-I090.AUD'],
  /** "Repairing" – a building is being repaired */
  evaRepairing: ['SPEECH01.MIX', '00-I040.AUD'],
  /** "Structure sold" */
  evaStructureSold: ['SPEECH01.MIX', '00-I228.AUD'],
  /** "Building offline" – switched off with the power button */
  evaBuildingOffline: ['SPEECH01.MIX', '00-I230.AUD'],
  /** "Building online" – switched on again */
  evaBuildingOnline: ['SPEECH01.MIX', '00-I232.AUD'],
  /** "Low power" – the base uses more power than it produces */
  evaLowPower: ['SPEECH01.MIX', '00-I024.AUD'],
  /** "Incoming transmission" – before a transmission appears in the radar */
  evaIncomingTransmission: ['SPEECH01.MIX', '00-I020.AUD'],
  /** "Mission accomplished" */
  evaMissionAccomplished: ['SPEECH01.MIX', '00-I026.AUD'],
  /** "Mission failed" */
  evaMissionFailed: ['SPEECH01.MIX', '00-I028.AUD'],
  /** "Timer stopped" */
  evaTimerStopped: ['SPEECH01.MIX', '00-I060.AUD'],
  /** Incoming message (IncomingMessage= in RULES.INI) */
  message: ['SOUNDS.MIX', 'MESSAGE1.AUD'],
  // the map of the briefing (sounds of the GDI map selection, [GDISFX] in MAPSEL.INI)
  /** The territories fade up over the map (Overlay=) */
  mapOverlay: ['SIDENC01.MIX', 'GSWEEP.AUD'],
  /** The crosshairs fly in (TargetFlyIn=) */
  mapTarget: ['SIDENC01.MIX', 'BESTBOX.AUD'],
  /** The cursor enters a target region (EnterRegion=) */
  mapEnter: ['SIDENC01.MIX', 'EFFICIEN.AUD'],
  /** A target region is clicked */
  mapClick: ['SIDENC01.MIX', 'CLKTARG.AUD'],
}

export type EvaSound = 'evaBuilding' | 'evaTraining' | 'evaConstructionComplete' | 'evaUnitReady' | 'evaNewOptions' | 'evaOnHold'
  | 'evaCancelled' | 'evaInsufficientFunds' | 'evaCannotPlace' | 'evaBuildingInProgress'
  | 'evaStartGame' | 'evaBaseAttack' | 'evaMissionAccomplished' | 'evaMissionFailed'
  | 'evaTimerStopped' | 'evaUnitLost' | 'evaHarvesterAttack' | 'evaLowPower' | 'evaIncomingTransmission'
  | 'evaRepairing' | 'evaStructureSold' | 'evaBuildingOffline' | 'evaBuildingOnline'
export type UiSound = 'open' | 'click' | 'radarOn' | 'radarOff' | 'message' | 'mapOverlay' | 'mapTarget' | 'mapEnter' | 'mapClick' | EvaSound

export async function loadUiSounds(ctx: BaseAudioContext, store: AssetStore) {
  const sounds: Partial<Record<UiSound, AudioBuffer>> = {}
  const tibsun = await store.get('TIBSUN.MIX')
  if (!tibsun) return sounds
  const archive = await MixArchive.open(tibsun, 'TIBSUN.MIX')
  const nested = new Map<string | number, MixArchive | undefined>()
  for (const [key, [mix, file]] of Object.entries(UI_SOUNDS) as [UiSound, readonly [string | number, number | string]][]) {
    if (!nested.has(mix)) nested.set(mix, await archive.openNested(mix))
    const entry = typeof file === 'number' ? nested.get(mix)?.entryByHash(file) : nested.get(mix)?.entry(file)
    const bytes = entry && await nested.get(mix)!.read(entry)
    if (bytes) sounds[key] = toAudioBuffer(ctx, decodeAud(bytes))
  }
  return sounds
}
