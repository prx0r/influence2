# Faceless Pianist Engine — Technical Spec v1

*Piano rolls give notes. Live recordings give soul. MIDI drives eyes, audio drives ears.*

---

## Core principle

**MIDI is for seeing. Audio is for hearing. Never cross the streams.**

- Hands visualize from MIDI (note-perfect timing, velocity-mapped curl)
- Ears hear the live recording (human touch, room, breathing, pedal noise)
- Sync layer aligns them (offset + drift correction, see §4)
- Atmosphere sweetens both (room tone, vinyl warmth, rain — optional layers)

What MIDI loses vs live: micro-timing push/pull, uneven voicing between hands,
half-pedaling, finger legato vs pedal legato, breathing, bench creaks, room.
We keep ALL of that in the audio. MIDI only positions fingertips.

---

## 1. Inputs

| Input | Source | Format | Purpose |
|---|---|---|---|
| MIDI (performance) | Piano roll (SUPRA/pianorollmusic) or transcribed (Kong/MT3) | `.mid` Type 1, 480+ TPQ | Fingertip targets + timing |
| Audio (performance) | Live recording (same piece, ideally same performer) | `.wav` 48kHz/24-bit | What the audience hears |
| Room splat | Marble/Atlas generate | `.spz` ~30MB | Venue (static) |
| Piano mesh | Marble generate (separate) or procedural 88-key | `.glb` or built-in | Keybed (keys depress per MIDI) |

**MIDI-audio pairing:** same piece, not necessarily same performance. Chopin
Nocturne MIDI (roll) + Rubinstein recording (audio) = hands play roll timing,
ears hear Rubinstein soul. Sync layer (§4) aligns downbeats; rubato differences
absorb into ±200ms visual tolerance (invisible at sleep distance).

---

## 2. MIDI → hands pipeline

```
MIDI file
  → parse (mido/midiutil): [(pitch, onset_ms, offset_ms, velocity 0-127)]
    → key map (pitch 21-108 → x position on 88-key bed, fixed geometry)
      → hand assign (pitch < 60 → left, ≥ 60 → right; crossings override)
        → finger assign (greedy: nearest free finger, thumb < index < ... < pinky)
          → fingertip targets [{x, y, z, t_start, t_end, curl_depth}]
            → IK solve (wrist → fingertip, 2-bone arm, elbow hint outward)
              → render (hand mesh + sleeve + cuff, stylized)
```

**Finger assignment rules:**
- Monophonic line: alternate 1-2-3-2-1 (thumb pivots, no crossing visible)
- Chords (3+ simultaneous): spread across available fingers, thumb on lowest
- Octaves: thumb + pinky (1+5), classic shape, always reads correctly
- Runs: sequential fingers 1-2-3-4-5-4-3-2-1 (scale fingering, universally legible)
- Crossings (thumb-under): simplified — fade thumb through (no one sees the tuck at sleep distance)

**Curl depth from velocity:** `curl = 0.3 + (velocity/127) * 0.7`. Fortissimo =
deep key dip, visible finger arch. Pianissimo = shallow touch, fingers hover.
This is where musicality reads visually — dynamics become gesture.

**Pedal:** sustain CC64 → glow under piano (subtle light swell, not literal pedal
mesh). Half-pedal → partial glow. Tells the ear's story to the eye without
modeling a foot nobody sees.

---

## 3. Audio pipeline (live recording, sweetened not synthesized)

```
Original recording (WAV/FLAC, any source)
  → loudness normalize to -20 LUFS (sleep standard)
    → true-peak limit -1.0 dBTP (no Bluetooth clipping)
      → gentle low-pass @ 12kHz, 6dB/oct (phone speaker kindness)
        → [OPTIONAL] atmosphere layers (see §5)
          → ship (WAV master → MP3 320k for upload)
```

**Forbidden:** reverb (room is in the recording), compression beyond limiting
(dynamics are the interpretation), EQ beyond low-pass (touch lives in mids),
noise reduction aggressive enough to gate pedal/room (that's the soul).

**Required metadata:** performer, recording date, source (Musopen/Roll transfer/
licensed), normalization receipt (input LUFS → output LUFS, limiter GR max).

---

## 4. Sync layer (MIDI eyes ↔ live ears)

**Problem:** MIDI (roll, 1905 tempo) and audio (recording, 1962 tempo) drift.
Same notes, different rubato, different total duration (±10-30s over 4 min).

**Solution: anchor-based warp (not time-stretch audio — never touch the audio).**

```
1. Detect anchors: downbeats of each phrase (first chord of each 4-8 bar section)
   in BOTH MIDI (note onsets) and audio (onset detection / manual marks)
2. Build warp map: MIDI_time → audio_time via piecewise-linear between anchors
3. Hands render on audio clock: fingertip target time = warp(MIDI onset)
4. Between anchors: linear interpolation (drift <200ms, invisible)
5. Validate: max drift per anchor gap <500ms else flag for manual anchor
```

**Tolerance budget:**
- ±0-100ms: imperceptible (all content passes)
- ±100-200ms: invisible at sleep distance (ship it)
- ±200-500ms: noticeable on close inspection (add anchor)
- ±500ms+: visible disconnect (manual fix required, usually wrong anchor)

**Never:** time-stretch the audio to fit MIDI (destroys rubato = destroys soul).
Always warp the visualization to fit the audio. Ears lead, eyes follow.

---

## 5. Atmosphere layers (optional, additive, toggleable)

| Layer | Source | Level | Purpose |
|---|---|---|---|
| Room tone | Recorded empty room (or synth brown noise -18dB) | -30 LUFS bed | Fills digital silence between phrases |
| Vinyl warmth | Filtered crackle loop (public domain sample) | -40 LUFS, high-passed | Nostalgia cue for historical recordings |
| Rain | Freesound CC0 loop | -35 LUFS, sidechained -3dB under piano | Sleep cue (Classical Nights signature) |
| Fire | Fireplace loop | -38 LUFS | Alternative to rain (winter pieces) |
| Page turn | Single sample at movement breaks | -25 LUFS transient | Human presence cue (someone's there) |
| Breath | Filtered noise swell on phrase peaks | -42 LUFS | Subconscious human proximity |

**Rules:** max 2 layers active simultaneously. Total atmosphere bed never exceeds
-28 LUFS (piano always dominant by 8dB+). All layers sidechain-ducked 2dB under
piano transients (MIDI velocity >100 triggers duck). Toggleable per video —
A/B test rain vs fire vs dry.

---

## 6. Camera grammar (5 locked angles, dissolve only)

| Camera | Frames | Audio pairing | Hold |
|---|---|---|---|
| Keys macro | Fingertips + 2 octaves, shallow DOF | Exposed passages (runs, trills) | 40% |
| Hands + cuffs | Wrists, sleeves, crossings | Active sections (both hands busy) | 30% |
| Silhouette wide | Bowed head, lamp halo, piano curve | Openings, closings, sparse sections | 20% |
| Window side | Profile silhouette vs rain/moon | Slow movements, nocturnes | 5% |
| Overhead | Key geometry, hand patterns | Fugues, counterpoint (visual logic) | 5% |

**Movement:** ≤0.5°/s drift within angle (barely alive, never distracting).
**Transitions:** 2s dissolve only, on phrase boundaries (never mid-phrase).
**Angle changes:** every 2-4 minutes, driven by musical structure (new section =
potential new angle, not mandatory).

---

## 7. Render pipeline (per video)

```
Inputs: MIDI + audio (synced) + room.spz + piano mesh + atmosphere prefs
  → validate sync (max drift check, §4)
    → render hands timeline (fingertip targets → IK → mesh frames)
      → composite scene (room splat + piano + hands + silhouette + candles)
        → render 5 camera angles (parallel, same scene, different viewpoints)
          → edit (dissolve on phrase boundaries per camera grammar)
            → mux (video + sweetened audio + atmosphere)
              → QC (sync spot-check 3 timestamps, loudness verify -20±1 LUFS)
                → ship (YouTube unlisted + Spotify podcast + receipt)
```

**Output specs:**
- Video: 1920×1080 h264, 24fps (cinematic, not 30/60 — sleep = slow), yuv420p, faststart
- Audio: AAC 320k (YouTube) + MP3 320k (podcast RSS) from same WAV master
- Duration: full piece, no cuts (Chopin Nocturne = ~4min, Goldberg = album-length project later)

---

## 8. File layout (per piece)

```
pieces/<composer>-<opus>/
  performance.mid       # roll or transcribed MIDI (eyes)
  performance.wav       # live recording master (ears, normalized)
  performance.mp3       # RSS/podcast distribution
  sync.json             # anchors + warp map + max drift
  hands.json            # fingertip timeline (cached render input)
  room.spz -> ../../venues/concert-room.spz (symlink, shared)
  cameras.json          # 5 angles + dissolve edit decision list
  atmosphere.json       # active layers + levels
  output.mp4            # final video
  receipt.json          # QC: sync spots, LUFS, sources, attributions
```

**Shared (not per-piece):**
```
venues/concert-room.spz     # Marble room (one-time generate)
venues/piano.glb            # piano mesh (one-time)
hands/rig.json              # hand IK rig (one-time build)
atmosphere/loops/*.wav     # room tone, rain, fire, vinyl (library)
```

---

## 9. What we explicitly do NOT build (v1)

- Faces, eyes, identity (faceless by design — see prior spec)
- Full body (torso suggested by silhouette, arms fade to dark)
- Real-time rendering (offline render → upload; live comes at Stage 5)
- Key depression mesh (keys static unless macro shot demands it — v2)
- Pedal foot (glow cue suffices — nobody sees feet in the dark)
- Multi-pianist (duets need two hand rigs + bench space — v2)
- GPU inference at render (transcription offline once, IK is CPU math)

---

## 10. Acceptance criteria (pilot: Chopin Nocturne Op.9 No.2)

- [ ] MIDI loaded (roll or transcribed, ≥95% note accuracy vs score)
- [ ] Audio normalized (-20±1 LUFS, -1.0 dBTP, documented source)
- [ ] Sync validated (max drift <500ms across all anchors)
- [ ] Hands render (all notes have fingertip targets, no floating fingers)
- [ ] 3 cameras rendered (keys, hands, wide — minimum viable)
- [ ] 4-min MP4 plays start-to-finish without glitch
- [ ] Uploaded unlisted to YouTube + podcast RSS draft ready
- [ ] Retention baseline measured vs static-image version
