#!/usr/bin/env python3
"""Real-time Barn Monitor — continuous frame analysis from video/camera.

Processes a video file or RTSP camera stream at configurable intervals,
analyzes each frame with Cosmos Reason 2, and sends alerts on anomalies.

Usage:
    # From video file (simulated real-time)
    python3 barn_monitor_realtime.py --video sample_videos/barn_example.mp4

    # From RTSP camera (Tapo or similar)
    python3 barn_monitor_realtime.py --camera "rtsp://user:pass@ip:554/stream1"

    # With Telegram alerts
    python3 barn_monitor_realtime.py --video sample_videos/barn_example.mp4 --alert

    # Fast demo (analyze every 5th second)
    python3 barn_monitor_realtime.py --video sample_videos/barn_example.mp4 --interval 5
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

# Import from our monitor module
sys.path.insert(0, str(Path(__file__).parent))
from horse_barn_monitor import (
    analyze_frame,
    check_server,
    start_server,
    send_telegram_alert,
    SEVERITY_LEVELS,
)


def extract_frame_at(source: str, timestamp: float, output_path: str) -> bool:
    """Extract a single frame at a given timestamp using ffmpeg."""
    cmd = [
        "ffmpeg",
        "-ss", str(timestamp),
        "-i", source,
        "-frames:v", "1",
        "-q:v", "2",
        "-y",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=30)
    return result.returncode == 0 and os.path.exists(output_path)


def get_video_duration(path: str) -> float:
    """Get video duration in seconds."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    try:
        return float(result.stdout.strip())
    except (ValueError, AttributeError):
        return 0.0


def monitor_video(
    video_path: str,
    interval: float = 5.0,
    alert: bool = False,
    output_dir: str = "monitoring_output",
    verbose: bool = False,
):
    """Monitor a video file, analyzing frames at regular intervals."""
    duration = get_video_duration(video_path)
    if duration <= 0:
        print(f"ERROR: Could not determine video duration: {video_path}")
        return

    os.makedirs(output_dir, exist_ok=True)
    print(f"\n🐴 Horse Barn Monitor — Real-time Mode")
    print(f"Video: {video_path} ({duration:.1f}s)")
    print(f"Analyzing every {interval:.0f}s → ~{int(duration / interval)} frames")
    print(f"Alerts: {'ON' if alert else 'OFF'}")
    print("=" * 60)

    results = []
    alert_count = 0
    t = 0.0
    frame_num = 0

    while t < duration:
        frame_num += 1
        frame_path = os.path.join(output_dir, f"frame_{frame_num:04d}.jpg")

        # Extract frame
        if not extract_frame_at(video_path, t, frame_path):
            print(f"[{t:6.1f}s] Failed to extract frame")
            t += interval
            continue

        # Analyze
        ts_str = f"{int(t//60):02d}:{int(t%60):02d}"
        print(f"[{ts_str}] Frame {frame_num}...", end=" ", flush=True)

        analysis = analyze_frame(frame_path, verbose=verbose)

        if "error" in analysis:
            print(f"ERROR: {analysis['error']}")
            t += interval
            continue

        severity = analysis.get("severity", "UNKNOWN")
        desc = analysis.get("description", "")[:60]
        latency = analysis.get("latency_s", 0)
        state = analysis.get("horse_state", "?")

        color = {
            "SAFE": "\033[92m",
            "MONITOR": "\033[93m",
            "WARNING": "\033[91m",
            "DANGER": "\033[1;91m",
        }.get(severity, "")
        reset = "\033[0m"

        print(f"{color}{severity:8}{reset} [{state:12}] {desc} ({latency:.1f}s)")

        # Alert on WARNING/DANGER
        sev_level = SEVERITY_LEVELS.get(severity, 0)
        if sev_level >= 2:
            alert_count += 1
            analysis["video_timestamp"] = ts_str
            if alert:
                send_telegram_alert(analysis)

        analysis["video_timestamp_s"] = t
        results.append(analysis)
        t += interval

    # Summary
    print("\n" + "=" * 60)
    print(f"Monitoring Complete: {frame_num} frames over {duration:.0f}s")
    safe = sum(1 for r in results if r.get("severity") == "SAFE")
    monitor = sum(1 for r in results if r.get("severity") == "MONITOR")
    warning = sum(1 for r in results if r.get("severity") == "WARNING")
    danger = sum(1 for r in results if r.get("severity") == "DANGER")
    print(f"  SAFE: {safe}  MONITOR: {monitor}  WARNING: {warning}  DANGER: {danger}")
    if alert_count > 0:
        print(f"  Alerts sent: {alert_count}")
    if results:
        avg_lat = sum(r.get("latency_s", 0) for r in results) / len(results)
        print(f"  Avg latency: {avg_lat:.1f}s")

    # Save timeline
    out_path = os.path.join(output_dir, "timeline.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nTimeline saved to {out_path}")

    return results


def monitor_camera(
    rtsp_url: str,
    interval: float = 10.0,
    alert: bool = True,
    output_dir: str = "monitoring_output",
    max_frames: int = 0,
    verbose: bool = False,
):
    """Monitor a live RTSP camera stream."""
    os.makedirs(output_dir, exist_ok=True)
    print(f"\n🐴 Horse Barn Monitor — Live Camera Mode")
    print(f"Camera: {rtsp_url[:50]}...")
    print(f"Interval: {interval}s")
    print(f"Alerts: {'ON' if alert else 'OFF'}")
    print("=" * 60)
    print("Press Ctrl+C to stop\n")

    results = []
    frame_num = 0
    alert_count = 0

    try:
        while True:
            frame_num += 1
            if max_frames > 0 and frame_num > max_frames:
                break

            frame_path = os.path.join(output_dir, f"live_{frame_num:04d}.jpg")

            # Capture frame from RTSP
            cmd = [
                "ffmpeg",
                "-rtsp_transport", "tcp",
                "-i", rtsp_url,
                "-frames:v", "1",
                "-q:v", "2",
                "-y",
                frame_path,
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            if result.returncode != 0:
                print(f"[Frame {frame_num}] Capture failed, retrying in {interval}s...")
                time.sleep(interval)
                continue

            now = datetime.now().strftime("%H:%M:%S")
            print(f"[{now}] Frame {frame_num}...", end=" ", flush=True)

            analysis = analyze_frame(frame_path, verbose=verbose)

            if "error" in analysis:
                print(f"ERROR: {analysis['error']}")
                time.sleep(interval)
                continue

            severity = analysis.get("severity", "UNKNOWN")
            desc = analysis.get("description", "")[:60]
            latency = analysis.get("latency_s", 0)
            state = analysis.get("horse_state", "?")

            color = {
                "SAFE": "\033[92m",
                "MONITOR": "\033[93m",
                "WARNING": "\033[91m",
                "DANGER": "\033[1;91m",
            }.get(severity, "")
            reset = "\033[0m"

            print(f"{color}{severity:8}{reset} [{state:12}] {desc} ({latency:.1f}s)")

            sev_level = SEVERITY_LEVELS.get(severity, 0)
            if sev_level >= 2:
                alert_count += 1
                if alert:
                    send_telegram_alert(analysis)

            results.append(analysis)

            # Wait for next interval (subtract analysis time)
            wait = max(0, interval - latency)
            if wait > 0:
                time.sleep(wait)

    except KeyboardInterrupt:
        print("\n\nStopping monitor...")

    # Save
    print(f"\nProcessed {frame_num} frames, {alert_count} alerts")
    if results:
        out_path = os.path.join(output_dir, "live_timeline.json")
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Timeline saved to {out_path}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Real-time Barn Monitor")
    parser.add_argument("--video", help="Video file to monitor")
    parser.add_argument("--camera", help="RTSP camera URL")
    parser.add_argument("--interval", type=float, default=5.0, help="Seconds between frames")
    parser.add_argument("--alert", action="store_true", help="Send Telegram alerts")
    parser.add_argument("--output", default="monitoring_output", help="Output directory")
    parser.add_argument("--max-frames", type=int, default=0, help="Max frames (0=unlimited)")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument(
        "--no-server-check",
        action="store_true",
        help="Skip server health check",
    )

    args = parser.parse_args()

    # Check server
    if not args.no_server_check:
        if not check_server():
            print("Starting Cosmos server...")
            if not start_server():
                sys.exit(1)
        else:
            print("Cosmos server: OK")

    if args.video:
        monitor_video(
            args.video,
            interval=args.interval,
            alert=args.alert,
            output_dir=args.output,
            verbose=args.verbose,
        )
    elif args.camera:
        monitor_camera(
            args.camera,
            interval=args.interval,
            alert=args.alert,
            output_dir=args.output,
            max_frames=args.max_frames,
            verbose=args.verbose,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
