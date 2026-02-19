#!/bin/bash
# StableWatch Demo Recording Script
# Records terminal output for Cosmos Cookoff Devpost submission
# Run with: bash demo_record.sh | tee demo_output.txt

set -e
cd "$(dirname "$0")"

BOLD="\033[1m"
GREEN="\033[92m"
RED="\033[91m"
YELLOW="\033[93m"
CYAN="\033[96m"
RESET="\033[0m"

echo ""
echo -e "${BOLD}════════════════════════════════════════════════════${RESET}"
echo -e "${BOLD}  🐴 StableWatch — AI Horse Barn Safety Monitor${RESET}"
echo -e "${BOLD}  Powered by NVIDIA Cosmos Reason 2 (8B)${RESET}"
echo -e "${BOLD}  Zero-shot • Local inference • Apple Silicon${RESET}"
echo -e "${BOLD}════════════════════════════════════════════════════${RESET}"
echo ""

# Check server
echo -e "${CYAN}▸ Checking Cosmos Reason 2 server...${RESET}"
if curl -s http://127.0.0.1:8095/health | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('status')=='ok' else 1)" 2>/dev/null; then
    echo -e "  ${GREEN}✅ Cosmos Reason 2 (8B, Q8_0) running on localhost:8095${RESET}"
else
    echo "  Starting server..."
    bash ~/Documents/TsubasaWorkspace/cortex/start_cosmos_server.sh
fi
echo ""
sleep 1

# ─── Demo 1: Normal barn (should be SAFE) ───
echo -e "${BOLD}═══ Demo 1: Normal Barn — Baseline (Expected: SAFE) ═══${RESET}"
echo ""
echo -e "Analyzing: ${CYAN}Two horses standing calmly in stalls${RESET}"
echo ""
python3 horse_barn_monitor.py --frame frames/barn_example_0030.jpg --no-server-check -v
echo ""
sleep 2

# ─── Demo 2: Barn Fire (should be DANGER) ───
echo -e "${BOLD}═══ Demo 2: Barn Fire — Emergency Detection ═══${RESET}"
echo ""
echo -e "Analyzing: ${RED}Barn with visible smoke and flames${RESET}"
echo ""
python3 horse_barn_monitor.py --frame frames_danger/barn_fire_0004.jpg --no-server-check -v
echo ""
sleep 2

# ─── Demo 3: Casting (should be DANGER) ───
echo -e "${BOLD}═══ Demo 3: Horse Casting — Trapped Against Wall ═══${RESET}"
echo ""
echo -e "Analyzing: ${RED}Mare and foal, horse lying near wall${RESET}"
echo ""
python3 horse_barn_monitor.py --frame frames_danger/casting_mare_foal_0030.jpg --no-server-check -v
echo ""
sleep 2

# ─── Demo 4: Real-time monitoring with escalation ───
echo -e "${BOLD}═══ Demo 4: Real-time Monitoring — Casting Video ═══${RESET}"
echo ""
echo -e "Simulating live barn camera analyzing a casting incident..."
echo -e "Watch how severity ${GREEN}escalates${RESET} as the situation develops."
echo ""
python3 barn_monitor_realtime.py --video sample_videos/casting_mare_foal.mp4 --interval 8 --output demo_output --no-server-check
echo ""
sleep 1

# ─── Demo 5: Real-time monitoring — Fire ───
echo -e "${BOLD}═══ Demo 5: Real-time Monitoring — Fire Detection ═══${RESET}"
echo ""
echo -e "Simulating barn fire incident..."
echo ""
python3 barn_monitor_realtime.py --video sample_videos/barn_fire.mp4 --interval 10 --output demo_output --no-server-check
echo ""

# ─── Summary ───
echo ""
echo -e "${BOLD}════════════════════════════════════════════════════${RESET}"
echo -e "${BOLD}  🐴 StableWatch Demo Complete${RESET}"
echo -e "${BOLD}════════════════════════════════════════════════════${RESET}"
echo ""
echo -e "  ${GREEN}✓${RESET} 16 hazard categories across 4 domains"
echo -e "  ${GREEN}✓${RESET} 4 severity levels: SAFE → MONITOR → WARNING → DANGER"
echo -e "  ${GREEN}✓${RESET} Zero-shot detection — no training data needed"
echo -e "  ${GREEN}✓${RESET} Local inference on Apple Silicon (~5-9s/frame)"
echo -e "  ${GREEN}✓${RESET} Real-time alerts via Telegram"
echo ""
echo -e "  Model: NVIDIA Cosmos Reason 2 (8B, Q8_0)"
echo -e "  Repo:  github.com/tsubasa-rsrch/stablewatch"
echo ""
