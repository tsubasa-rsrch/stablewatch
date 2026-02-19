#!/bin/bash
# StableWatch Demo Recording Script
# Records terminal output for Devpost submission

set -e
cd "$(dirname "$0")"

echo "========================================"
echo "  🐴 StableWatch — Demo Recording"
echo "  NVIDIA Cosmos Cookoff 2026"
echo "========================================"
echo ""

# Check server
echo "Step 1: Checking Cosmos Reason 2 server..."
if curl -s http://127.0.0.1:8095/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  Server: {d[\"status\"]}') if d.get('status')=='ok' else sys.exit(1)" 2>/dev/null; then
    echo "  ✅ Cosmos Reason 2 (8B) ready"
else
    echo "  Starting Cosmos server..."
    bash ~/Documents/TsubasaWorkspace/cortex/start_cosmos_server.sh
fi
echo ""

# Demo 1: Single frame analysis
echo "========================================"
echo "  Demo 1: Single Frame Analysis"
echo "========================================"
echo ""
echo "Analyzing: barn_example_0030.jpg (two horses in stalls)"
python3 horse_barn_monitor.py --frame frames/barn_example_0030.jpg --no-server-check
echo ""

# Demo 2: Batch analysis with various scenarios
echo "========================================"
echo "  Demo 2: Batch Analysis (8 frames)"
echo "========================================"
echo ""
python3 horse_barn_monitor.py --dir frames/ --sample 8 --no-server-check
echo ""

# Demo 3: Real-time video monitoring
echo "========================================"
echo "  Demo 3: Real-time Video Monitoring"
echo "========================================"
echo ""
echo "Simulating live barn camera feed..."
python3 barn_monitor_realtime.py --video sample_videos/barn_stall.mp4 --interval 8 --output demo_recording_output
echo ""

echo "========================================"
echo "  Demo Complete! 🐴"
echo "  StableWatch: Zero-shot horse safety"
echo "  monitoring with Cosmos Reason 2"
echo "========================================"
