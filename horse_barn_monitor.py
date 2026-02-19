#!/usr/bin/env python3
"""Horse Barn Safety Monitor — Cosmos Reason 2 + Zero-shot Inference.

Analyzes barn camera frames for horse safety anomalies using
NVIDIA Cosmos Reason 2 (8B, local via llama-server).

Detects: casting, entanglement, prolonged lying, colic signs,
fire/smoke, escape, foaling difficulties.

Usage:
    # Analyze a single frame
    python3 horse_barn_monitor.py --frame frames/barn_example_0001.jpg

    # Analyze all frames in a directory
    python3 horse_barn_monitor.py --dir frames/ --sample 5

    # Continuous monitoring (1fps from camera)
    python3 horse_barn_monitor.py --camera rtsp://... --interval 5

    # Demo mode: process sample videos
    python3 horse_barn_monitor.py --demo
"""

import argparse
import base64
import io
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Cosmos server config
COSMOS_HOST = "127.0.0.1"
COSMOS_PORT = 8095
COSMOS_URL = f"http://{COSMOS_HOST}:{COSMOS_PORT}/v1/chat/completions"
MAX_IMAGE_DIM = 512  # resize for ctx_size constraints
MAX_TOKENS = 1024
TEMPERATURE = 0.2  # low temp for consistent safety judgments

# Safety classification
SEVERITY_LEVELS = {
    "SAFE": 0,
    "MONITOR": 1,
    "WARNING": 2,
    "DANGER": 3,
}

# The core safety analysis prompt — based on real barn incident patterns
SAFETY_SYSTEM_PROMPT = """You are an equine safety monitoring AI analyzing barn camera footage.
Detect potential safety hazards for horses using physical reasoning.

Output JSON:
{
  "severity": "SAFE" | "MONITOR" | "WARNING" | "DANGER",
  "description": "Brief description of what you see",
  "hazards": ["list of detected hazards"],
  "horse_state": "standing" | "lying" | "rolling" | "moving" | "not_visible" | "eating" | "stressed",
  "confidence": 0.0 to 1.0,
  "recommended_action": "none" | "log" | "alert_owner" | "emergency"
}

HAZARD CATEGORIES (priority order):

Physical Injury Risk:
- CASTING: Horse trapped on back/side against wall, unable to stand
- ENTANGLEMENT: Legs caught in hay nets, ropes, fencing, water bucket snaps, equipment
- FALL_SLIP: Horse slipping on wet/icy floor, stumbling, fallen down
- KICK_BITE: Horses fighting, kicking stall walls, biting each other
- PROTRUSION: Exposed nails, broken wood, loose bolts, sharp metal edges near horse

Health Emergency:
- COLIC: Rolling repeatedly, looking at flanks, pawing ground, sweating, lying/standing cycles
- CHOKING: Extended neck, drooling, distress posture
- ABNORMAL_POSTURE: Legs splayed, head pressing against wall, hunched back

Environment & Equipment:
- FIRE_SMOKE: Smoke, flames, haze, spontaneous hay combustion signs
- ESCAPE: Broken fence, open gate, horse outside stall, door manipulation
- WET_FLOOR: Visible water pooling, ice, shifted mats
- TOOLS_DEBRIS: Equipment left in corridor, cords, obstacles in horse path
- AMMONIA: Excessive soiled bedding (dark wet patches covering most of floor)

Stress Behavior:
- CRIBBING: Biting wood surfaces, stall edges
- WEAVING: Repetitive side-to-side swaying
- WALL_KICKING: Repeated strikes against stall walls
- PACING: Repetitive walking pattern in circles

Severity guide:
- SAFE: Horse calm, environment clean, no hazards visible
- MONITOR: Minor concern (horse lying normally, mild mess, horse near fence)
- WARNING: Active concern (unusual posture, signs of stress, equipment hazard)
- DANGER: Emergency (casting, fire, severe entanglement, horse down and struggling)

Be conservative: escalate to WARNING rather than SAFE when uncertain.
Keep description under 80 words. Respond ONLY with raw JSON, no markdown."""

ANALYSIS_PROMPT = "Analyze this barn camera frame for horse safety. What do you see? Are there any hazards?"


def _extract_from_truncated(clean: str, raw: str) -> dict:
    """Extract fields from truncated JSON response via regex."""
    import re

    def _find(pattern, text, default=""):
        m = re.search(pattern, text)
        return m.group(1) if m else default

    severity = _find(r'"severity"\s*:\s*"(\w+)"', raw, "MONITOR")
    description = _find(r'"description"\s*:\s*"([^"]*)"', raw, raw[:200])
    horse_state = _find(r'"horse_state"\s*:\s*"([^"]*)"', raw, "unknown")
    confidence = float(_find(r'"confidence"\s*:\s*([\d.]+)', raw, "0.5"))
    action = _find(r'"recommended_action"\s*:\s*"([^"]*)"', raw, "log")

    # Extract hazards array
    hazards = []
    haz_match = re.search(r'"hazards"\s*:\s*\[(.*?)\]', raw, re.DOTALL)
    if haz_match:
        hazards = re.findall(r'"([^"]+)"', haz_match.group(1))

    return {
        "severity": severity,
        "description": description,
        "hazards": hazards,
        "horse_state": horse_state,
        "confidence": confidence,
        "recommended_action": action,
        "truncated": True,
    }


def encode_image(image_path: str) -> Optional[str]:
    """Encode and resize image to base64."""
    try:
        from PIL import Image
        img = Image.open(image_path)
        img.thumbnail((MAX_IMAGE_DIM, MAX_IMAGE_DIM))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except ImportError:
        # Fallback without PIL
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")


def check_server() -> bool:
    """Check if Cosmos server is running."""
    try:
        import urllib.request
        req = urllib.request.Request(f"http://{COSMOS_HOST}:{COSMOS_PORT}/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return data.get("status") == "ok"
    except Exception:
        return False


def start_server() -> bool:
    """Start the Cosmos Reason 2 server."""
    script = os.path.expanduser(
        "~/Documents/TsubasaWorkspace/cortex/start_cosmos_server.sh"
    )
    if not os.path.exists(script):
        print(f"ERROR: Server script not found: {script}")
        return False

    print("Starting Cosmos Reason 2 server...")
    subprocess.Popen(["bash", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Wait for server
    for i in range(30):
        if check_server():
            print(f"Server ready! ({i+1}s)")
            return True
        time.sleep(1)

    print("ERROR: Server failed to start after 30s")
    return False


def analyze_frame(image_path: str, verbose: bool = False) -> dict:
    """Send a frame to Cosmos Reason 2 for safety analysis."""
    import urllib.request

    img_data = encode_image(image_path)
    if not img_data:
        return {"error": f"Failed to encode image: {image_path}"}

    messages = [
        {"role": "system", "content": SAFETY_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_data}"},
                },
                {"type": "text", "text": ANALYSIS_PROMPT},
            ],
        },
    ]

    payload = {
        "model": "cosmos-reason2",
        "messages": messages,
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
        "stream": False,
    }

    start_time = time.time()
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            COSMOS_URL,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            text = (
                result.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )

        latency = time.time() - start_time

        # Parse JSON response
        clean = text.strip()
        # Strip markdown code fences (handle ```json ... ``` wrapping)
        import re
        fence_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', clean, re.DOTALL)
        if fence_match:
            clean = fence_match.group(1).strip()
        elif clean.startswith("```"):
            lines = clean.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            clean = "\n".join(lines)

        try:
            analysis = json.loads(clean)
        except json.JSONDecodeError:
            # Fallback: extract fields from truncated JSON via regex
            analysis = _extract_from_truncated(clean, text)

        analysis["latency_s"] = round(latency, 2)
        analysis["frame"] = os.path.basename(image_path)
        analysis["timestamp"] = datetime.now().isoformat()

        if verbose:
            print(f"  Raw response ({latency:.1f}s): {text[:200]}")

        return analysis

    except Exception as e:
        return {
            "error": str(e),
            "frame": os.path.basename(image_path),
            "timestamp": datetime.now().isoformat(),
        }


def send_telegram_alert(analysis: dict):
    """Send Telegram alert for WARNING/DANGER."""
    severity = analysis.get("severity", "UNKNOWN")
    desc = analysis.get("description", "Unknown")
    hazards = ", ".join(analysis.get("hazards", []))
    action = analysis.get("recommended_action", "check")
    frame = analysis.get("frame", "unknown")

    emoji = {"WARNING": "⚠️", "DANGER": "🚨"}.get(severity, "📋")

    msg = (
        f"{emoji} Horse Barn Alert: {severity}\n"
        f"Frame: {frame}\n"
        f"Description: {desc}\n"
    )
    if hazards:
        msg += f"Hazards: {hazards}\n"
    msg += f"Action: {action}"

    script = os.path.expanduser(
        "~/Documents/TsubasaWorkspace/tsubasa-daemon/telegram_reply.py"
    )
    try:
        subprocess.run(
            ["python3", script, msg],
            capture_output=True,
            timeout=10,
        )
        print(f"  Telegram alert sent!")
    except Exception as e:
        print(f"  Telegram alert failed: {e}")


def analyze_directory(
    frames_dir: str,
    sample: int = 0,
    verbose: bool = False,
    alert: bool = False,
):
    """Analyze frames from a directory."""
    frames = sorted(Path(frames_dir).glob("*.jpg"))
    if not frames:
        print(f"No .jpg frames found in {frames_dir}")
        return []

    if sample > 0:
        # Evenly sample frames
        step = max(1, len(frames) // sample)
        frames = frames[::step][:sample]

    print(f"\nAnalyzing {len(frames)} frames from {frames_dir}")
    print("=" * 60)

    results = []
    danger_count = 0
    warning_count = 0

    for i, frame in enumerate(frames):
        print(f"\n[{i+1}/{len(frames)}] {frame.name}...", end=" ", flush=True)
        analysis = analyze_frame(str(frame), verbose=verbose)

        if "error" in analysis:
            print(f"ERROR: {analysis['error']}")
            results.append(analysis)
            continue

        severity = analysis.get("severity", "UNKNOWN")
        desc = analysis.get("description", "")[:80]
        latency = analysis.get("latency_s", 0)
        state = analysis.get("horse_state", "?")

        color = {
            "SAFE": "\033[92m",      # green
            "MONITOR": "\033[93m",   # yellow
            "WARNING": "\033[91m",   # red
            "DANGER": "\033[1;91m",  # bold red
        }.get(severity, "")
        reset = "\033[0m"

        print(f"{color}{severity}{reset} ({latency:.1f}s) [{state}] {desc}")

        if severity == "DANGER":
            danger_count += 1
            if alert:
                send_telegram_alert(analysis)
        elif severity == "WARNING":
            warning_count += 1
            if alert:
                send_telegram_alert(analysis)

        results.append(analysis)

    # Summary
    print("\n" + "=" * 60)
    print(f"Summary: {len(results)} frames analyzed")
    print(f"  SAFE: {sum(1 for r in results if r.get('severity') == 'SAFE')}")
    print(f"  MONITOR: {sum(1 for r in results if r.get('severity') == 'MONITOR')}")
    print(f"  WARNING: {warning_count}")
    print(f"  DANGER: {danger_count}")

    if results:
        avg_latency = sum(r.get("latency_s", 0) for r in results) / len(results)
        print(f"  Avg latency: {avg_latency:.1f}s")

    # Save results
    out_path = Path(frames_dir).parent / "analysis_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_path}")

    return results


def demo_mode(verbose: bool = False):
    """Run demo with sample barn videos."""
    base = Path(__file__).parent
    frames_dir = base / "frames"

    if not frames_dir.exists() or not list(frames_dir.glob("*.jpg")):
        print("No frames found. Extracting from sample videos...")
        videos_dir = base / "sample_videos"
        videos = list(videos_dir.glob("*.mp4"))
        if not videos:
            print("ERROR: No sample videos found in sample_videos/")
            return

        frames_dir.mkdir(exist_ok=True)
        for video in videos:
            name = video.stem
            cmd = [
                "ffmpeg", "-i", str(video),
                "-vf", "fps=1",
                "-q:v", "2",
                str(frames_dir / f"{name}_%04d.jpg"),
                "-y",
            ]
            subprocess.run(cmd, capture_output=True)

        count = len(list(frames_dir.glob("*.jpg")))
        print(f"Extracted {count} frames")

    # Analyze a sample of frames (5 from each video)
    print("\n🐴 Horse Barn Safety Monitor — Demo Mode")
    print("Using NVIDIA Cosmos Reason 2 (8B, local inference)")
    analyze_directory(str(frames_dir), sample=10, verbose=verbose, alert=False)


def main():
    parser = argparse.ArgumentParser(
        description="Horse Barn Safety Monitor — Cosmos Reason 2"
    )
    parser.add_argument("--frame", help="Analyze a single frame")
    parser.add_argument("--dir", help="Analyze all frames in directory")
    parser.add_argument("--sample", type=int, default=0, help="Sample N frames evenly")
    parser.add_argument("--demo", action="store_true", help="Demo with sample videos")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--alert", action="store_true", help="Send Telegram alerts")
    parser.add_argument(
        "--no-server-check",
        action="store_true",
        help="Skip server health check",
    )

    args = parser.parse_args()

    # Check server
    if not args.no_server_check:
        if not check_server():
            print("Cosmos server not running. Starting...")
            if not start_server():
                print("Failed to start server. Run manually:")
                print("  bash ~/Documents/TsubasaWorkspace/cortex/start_cosmos_server.sh")
                sys.exit(1)
        else:
            print("Cosmos server: OK")

    if args.frame:
        print(f"\nAnalyzing: {args.frame}")
        result = analyze_frame(args.frame, verbose=args.verbose)
        print(json.dumps(result, indent=2))
        if args.alert and result.get("severity") in ("WARNING", "DANGER"):
            send_telegram_alert(result)

    elif args.dir:
        analyze_directory(args.dir, sample=args.sample, verbose=args.verbose, alert=args.alert)

    elif args.demo:
        demo_mode(verbose=args.verbose)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
