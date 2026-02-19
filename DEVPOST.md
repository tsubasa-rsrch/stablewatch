# StableWatch — Devpost Submission Text

## Project Title
StableWatch: AI Horse Barn Safety Monitor

## Tagline
Zero-shot equine safety monitoring powered by NVIDIA Cosmos Reason 2 — no training data, just physical reasoning.

## Inspiration

Every year, thousands of horses are injured or die from preventable barn accidents. **Casting** (a horse trapped against a wall, unable to stand) can be fatal within hours. **Hay net entanglement** can cause leg injuries. **Barn fires** need minute-level response times.

Existing barn cameras only record — they don't understand what they see. Horse owners check cameras manually, but emergencies happen at 3 AM when no one is watching.

We built StableWatch to add **physical AI reasoning** to any barn camera, using NVIDIA Cosmos Reason 2's understanding of spatial relationships, object states, and anomaly detection — with zero training data.

## What it does

StableWatch analyzes barn camera frames in real-time using Cosmos Reason 2, detecting **16 hazard categories** across 4 domains:

**Physical Injury**: Casting, entanglement, falls/slips, kicks, protrusions
**Health Emergency**: Colic signs, choking, abnormal posture
**Environment**: Fire/smoke, escape, wet floors, tools/debris, ammonia
**Stress Behavior**: Cribbing, weaving, wall kicking, pacing

Each frame receives a severity classification:
- **SAFE**: Normal behavior, no hazards
- **MONITOR**: Minor concern worth logging
- **WARNING**: Active concern requiring attention → alerts owner
- **DANGER**: Emergency requiring immediate action → emergency alert

## How we built it

**Architecture:**
```
Camera (RTSP/File) → FFmpeg (frame extraction) → Cosmos Reason 2 (8B) → Safety classification → Alert (Telegram)
```

**Key technical decisions:**
1. **Zero-shot approach**: Instead of collecting and labeling thousands of barn images, we leverage Cosmos Reason 2's physical reasoning to understand horse behavior from a detailed safety prompt. The model reasons about spatial relationships (horse near wall = potential casting), temporal patterns (repeated rolling = colic signs), and environmental hazards (smoke = fire).

2. **Local inference**: The entire system runs locally on Apple Silicon (M4 Max) using llama.cpp with the Q8_0 quantized model. No cloud API needed — critical for barn locations with limited internet.

3. **Structured JSON output**: The model returns machine-parseable JSON with severity, hazards, horse state, confidence, and recommended action — enabling automated alerting pipelines.

4. **Conservative bias**: The prompt instructs the model to escalate uncertainty to WARNING rather than SAFE, prioritizing horse safety over false alarm reduction.

## Challenges we ran into

1. **Single-frame limitations**: Fast events like door escapes happen in 1-2 seconds and are hard to catch with per-frame analysis at 10-second intervals. Future versions need temporal analysis across frame sequences.

2. **Model verbosity**: Cosmos Reason 2 sometimes generates markdown-wrapped or overly long responses, requiring robust fallback parsing (regex extraction from truncated JSON).

3. **Video quality variation**: Different camera angles, lighting conditions, and barn layouts affect detection confidence. The zero-shot approach handles this well, but dark nighttime footage remains challenging.

## Accomplishments we're proud of

- **Zero false alarms on normal barn footage**: 6 frames of calm horses, 0 false positives
- **100% fire detection**: 4/9 frames correctly classified as DANGER in barn fire footage
- **Correct severity escalation**: Casting video showed MONITOR → WARNING → DANGER progression
- **Real-world validation**: The hazard taxonomy was designed with input from an actual horse owner whose horse (Opi) has experienced hay net entanglement and barn door escape

## What we learned

- Cosmos Reason 2's physical reasoning is remarkably good at understanding animal behavior and spatial hazards — zero-shot, no fine-tuning needed
- The gap between "detection" and "understanding" is exactly what VLMs bridge: a traditional CV model can detect a horse lying down, but Cosmos can reason about *why* that might be dangerous (near a wall = casting risk)
- Real barn safety involves much more than just "horse is down" — equipment hazards, environmental risks, and stress behaviors all matter

## What's next for StableWatch

1. **Temporal analysis**: Analyze sequences of frames to detect time-dependent hazards (prolonged lying, repeated rolling)
2. **Edge deployment**: Run on NVIDIA Jetson for on-site inference at barns without reliable internet
3. **Real barn testing**: Deploy at an actual horse barn with Tapo cameras
4. **Multi-camera fusion**: Combine views from multiple cameras for better spatial understanding
5. **Night vision**: Optimize for infrared/night camera footage

## Built With
- NVIDIA Cosmos Reason 2 (8B, Q8_0)
- llama.cpp (llama-server)
- Python 3, FFmpeg, Pillow
- Apple Silicon (M4 Max 48GB)
- Telegram Bot API (for alerts)

## Try it out
- [GitHub Repository](https://github.com/tsubasa-rsrch/stablewatch)
