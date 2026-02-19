# 🐴 StableWatch — AI Horse Barn Safety Monitor

**Powered by NVIDIA Cosmos Reason 2 | Local inference on Apple Silicon**

StableWatch uses NVIDIA Cosmos Reason 2 (8B) to analyze barn camera footage in real-time, detecting safety hazards for horses. Zero-shot visual reasoning — no training data needed.

## The Problem

Every year, thousands of horses are injured or die from preventable barn accidents:
- **Casting**: Horse trapped against a wall, unable to stand
- **Entanglement**: Legs caught in hay nets, ropes, or fencing
- **Colic**: Repeated rolling, looking at flanks — early detection saves lives
- **Fire/Smoke**: Minutes matter in barn fires

Existing barn cameras only record — they don't understand what they see.

## The Solution

StableWatch adds **physical AI reasoning** to any barn camera:

```
Camera → Frame extraction → Cosmos Reason 2 → Safety classification → Alert
```

### Key Features

- **Zero-shot detection**: No training data required. Cosmos Reason 2's physical reasoning understands horse behavior out of the box
- **16 hazard categories** across 4 domains: physical injury, health emergency, environment, stress behavior
- **4-level severity**: SAFE → MONITOR → WARNING → DANGER
- **Real-time alerts**: Telegram notifications on WARNING/DANGER events
- **Fully local**: Runs on M4 Max MacBook Pro — no cloud API needed
- **5.5s per frame**: Fast enough for continuous monitoring at 1 frame every 10 seconds

### Detection Examples

| Scenario | Severity | Response |
|----------|----------|----------|
| Horse standing normally | SAFE | Log only |
| Horse lying down briefly | MONITOR | Log + timestamp |
| Horse near open gate | MONITOR | Log + monitor |
| Horse lying for extended period | WARNING | Alert owner |
| Repeated rolling (colic signs) | WARNING | Alert owner |
| Stress behavior (wall kicking) | WARNING | Alert owner |
| Horse trapped/cast against wall | DANGER | Emergency alert |
| Legs entangled in hay net | DANGER | Emergency alert |
| Smoke/fire detected in barn | DANGER | Emergency alert |

### Hazard Categories

| Domain | Categories |
|--------|-----------|
| Physical Injury | Casting, Entanglement, Fall/Slip, Kick/Bite, Protrusion |
| Health Emergency | Colic, Choking, Abnormal Posture |
| Environment | Fire/Smoke, Escape, Wet Floor, Tools/Debris, Ammonia |
| Stress Behavior | Cribbing, Weaving, Wall Kicking, Pacing |

## Architecture

```
┌─────────────┐     ┌──────────┐     ┌──────────────────┐     ┌──────────┐
│ Barn Camera  │────▶│  FFmpeg  │────▶│ Cosmos Reason 2  │────▶│  Alert   │
│ (RTSP/File)  │     │ (1 fps)  │     │  (8B, Q8_0)      │     │(Telegram)│
└─────────────┘     └──────────┘     └──────────────────┘     └──────────┘
                                            │
                                     Local inference
                                     M4 Max, ~5.5s/frame
```

## Quick Start

```bash
# 1. Start Cosmos Reason 2 server
bash start_cosmos_server.sh

# 2. Analyze a single frame
python3 horse_barn_monitor.py --frame path/to/frame.jpg

# 3. Monitor a video file
python3 barn_monitor_realtime.py --video barn_footage.mp4 --interval 10

# 4. Monitor a live camera (with alerts)
python3 barn_monitor_realtime.py --camera "rtsp://user:pass@ip:554/stream1" --alert

# 5. Demo mode
python3 horse_barn_monitor.py --demo
```

## Requirements

- **Hardware**: Apple Silicon Mac (M1+ for inference, M4 Max recommended)
- **Model**: Cosmos-Reason2-8B.Q8_0.gguf (8.1GB) + mmproj (1.1GB)
- **Software**: llama.cpp (llama-server), Python 3.10+, FFmpeg, Pillow
- **Optional**: Telegram bot for alerts

## Model

Uses [NVIDIA Cosmos Reason 2](https://developer.nvidia.com/cosmos) (8B parameter):
- Based on Qwen3-VL architecture
- Quantized to Q8_0 for local inference
- Physical AI reasoning: understands spatial relationships, object states, anomalies
- 262K context window

## Real-World Deployment Plan

1. **WiFi available**: Install Tapo camera → RTSP stream → StableWatch on local device
2. **No WiFi**: SIM-equipped camera or IoT solution (Soracom) → cloud relay → StableWatch
3. **Edge deployment**: NVIDIA Jetson for on-site inference

## Danger Scenario Test Results

Tested on casting, barn fire, and colic videos:

| Scenario | Frames | DANGER | WARNING | Detection |
|----------|--------|--------|---------|-----------|
| Barn fire | 9 | 4 | 1 | Fire/smoke detected at confidence 0.99-1.0 |
| Casting (mare+foal) | 10 | 2 | 4 | Correct escalation: MONITOR→WARNING→DANGER |
| Casting (stall) | 13 | 0 | 1 | Calmer video, caught lying horse |
| Colic (staggering) | 5 | 0 | 2 | Detected transition from eating to lying |
| Normal barn | 6 | 0 | 0 | Correct baseline — no false alarms |

## Performance

| Metric | Value |
|--------|-------|
| Avg inference time | 5.5-9s per frame |
| Model size | 8.1 GB (Q8_0) |
| Memory usage | ~10 GB |
| Monitoring interval | 10s recommended |
| Hardware | M4 Max 48GB |

## File Structure

```
cosmos-cookoff/
├── horse_barn_monitor.py       # Core analysis engine
├── barn_monitor_realtime.py    # Real-time video/camera monitor
├── sample_videos/              # Test footage
├── frames/                     # Extracted frames
├── monitoring_output/          # Analysis timeline & frames
└── README.md
```

## NVIDIA Cosmos Cookoff Submission

- **Challenge**: Build with Cosmos models
- **Category**: Physical AI / Safety
- **Model**: Cosmos Reason 2 (8B)
- **Innovation**: Zero-shot equine safety monitoring — no training data, just physical reasoning

## License

MIT

---

*Built with care for Opi and all horses. 🐴*
*NVIDIA Cosmos Cookoff 2026*
