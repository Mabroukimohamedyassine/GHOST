#!/bin/bash
# ==============================================================================
# GHOST v3 — Workstation Entrypoint Script
# ==============================================================================
# This script is the "brain" of Container B. It executes four critical phases
# every time the container boots:
#
#   Phase 1: Dynamic Tool Installation  — Install user-requested Kali packages
#   Phase 2: Routing Handcuffs          — Force ALL traffic through the Gateway
#   Phase 3: Volume Preparation         — Ensure mount points exist
#   Phase 4: Headless GUI Boot          — Start display → desktop → VNC → noVNC
#
# The script is designed to be idempotent and error-tolerant: if a non-critical
# step fails, it logs a warning and continues. Only routing failures are fatal.
# ==============================================================================

set -e  # Exit on critical errors (we selectively disable this where needed)

# --- Configuration -----------------------------------------------------------
GATEWAY_IP="${GATEWAY_IP:-10.0.0.2}"  # IP of the Tor Gateway (Container A)
DISPLAY_NUM=":1"                       # Virtual display number for Xvfb
DISPLAY_RES="1280x800x24"             # Resolution: width x height x color depth
VNC_PORT="5901"                        # VNC server listening port
NOVNC_PORT="8080"                      # noVNC web interface port
NOVNC_PATH="/usr/share/novnc"         # Path to noVNC web files

export DISPLAY="${DISPLAY_NUM}"

# --- Logging Helper -----------------------------------------------------------
log_info()    { echo -e "\033[0;36m[*] GHOST-WS:\033[0m $1"; }
log_success() { echo -e "\033[0;32m[✓] GHOST-WS:\033[0m $1"; }
log_warn()    { echo -e "\033[1;33m[!] GHOST-WS:\033[0m $1"; }
log_error()   { echo -e "\033[0;31m[✗] GHOST-WS:\033[0m $1"; }

# ==============================================================================
# PHASE 1: DYNAMIC TOOL INSTALLATION
# ==============================================================================
# Theory: Instead of baking every possible pentesting tool into the Docker image
# (which would make it enormous), we let the user specify what they need via the
# KALI_METAPACKAGES environment variable in .env. This keeps the base image lean
# and allows per-engagement customization.
#
# Example: KALI_METAPACKAGES="nmap sqlmap dirb burpsuite"
# ==============================================================================

log_info "Phase 1: Checking for dynamic tool installation..."

if [ -n "$KALI_METAPACKAGES" ]; then
    log_info "Packages requested: $KALI_METAPACKAGES"
    log_info "Updating package lists..."

    set +e  # Don't exit on apt failures — they're non-critical
    apt-get update -qq 2>/dev/null

    # shellcheck disable=SC2086
    # We intentionally word-split KALI_METAPACKAGES to pass each package as
    # a separate argument to apt-get.
    apt-get install -y --no-install-recommends $KALI_METAPACKAGES 2>&1 | \
        tail -n 5  # Only show last 5 lines to reduce boot noise

    if [ $? -eq 0 ]; then
        log_success "Dynamic packages installed successfully."
    else
        log_warn "Some packages may have failed to install. Continuing boot..."
    fi

    # Clean up apt cache to save container memory
    rm -rf /var/lib/apt/lists/*
    set -e  # Re-enable strict error handling
else
    log_info "No KALI_METAPACKAGES defined. Skipping dynamic installation."
fi

# ==============================================================================
# PHASE 2: THE ROUTING HANDCUFFS (CRITICAL)
# ==============================================================================
# Theory: This is the single most important security mechanism in the entire
# GHOST architecture. Even though the Docker network is set to "internal: true",
# we add a defense-in-depth layer by explicitly rewriting the container's
# routing table.
#
# What happens:
#   1. We DELETE the default gateway route that Docker automatically assigns.
#      This route normally points to the Docker bridge (172.x.x.x) which has
#      NAT access to the host's internet — a potential leak path.
#
#   2. We ADD a new default route pointing to the Gateway container (10.0.0.2).
#      Now every single packet leaving this container MUST pass through the
#      Tor transparent proxy. There is no alternative path.
#
# If this step fails, the container MUST NOT continue — it would be operating
# without anonymization, which is worse than not operating at all.
# ==============================================================================

log_info "Phase 2: Applying routing handcuffs..."

# Step 2a: Delete Docker's default gateway to prevent any bypass
if ip route del default 2>/dev/null; then
    log_success "Default gateway route removed."
else
    log_warn "No default route found to remove (may already be clean)."
fi

# Step 2b: Set the Gateway container as the ONLY path to the outside world
if ip route add default via "$GATEWAY_IP" 2>/dev/null; then
    log_success "Default route set to Gateway ($GATEWAY_IP)."
else
    log_error "FATAL: Failed to set route to Gateway. Aborting for safety."
    log_error "Without this route, traffic could leak outside Tor."
    exit 1
fi

# Step 2c: Verify the route is correctly applied
log_info "Current routing table:"
ip route show

log_success "Routing handcuffs applied. All traffic forced through $GATEWAY_IP."

# ==============================================================================
# PHASE 3: VOLUME MAPPING PREPARATION
# ==============================================================================
# Theory: The user's local files (wordlists, password files, custom scripts)
# are mounted into /root/ghost_files via Docker volumes defined in
# docker-compose.yml. We ensure this directory exists even if no volume is
# mounted, so scripts that reference it don't crash.
# ==============================================================================

log_info "Phase 3: Preparing volume mount points..."

mkdir -p /root/ghost_files
log_success "/root/ghost_files is ready."

if [ -d "/root/ghost_files" ] && [ "$(ls -A /root/ghost_files 2>/dev/null)" ]; then
    log_info "User files detected in /root/ghost_files:"
    ls -la /root/ghost_files/ | head -10
else
    log_info "No user files mounted. /root/ghost_files is empty."
fi

# ==============================================================================
# PHASE 4: HEADLESS GUI BOOT SEQUENCE
# ==============================================================================
# Theory: Pentesting tools like Burp Suite require a graphical interface.
# Since this container runs headless (no physical monitor), we create a
# "virtual monitor" pipeline:
#
#   Xvfb (Virtual Display) → XFCE4 (Desktop Environment) → x11vnc (VNC Server)
#       → websockify/noVNC (WebSocket bridge → HTML5 viewer in your browser)
#
# The user opens http://localhost:8080 and sees a full Kali desktop.
# ==============================================================================

log_info "Phase 4: Starting headless GUI stack..."

# --- Step 4a: Start Xvfb (Virtual Framebuffer) --------------------------------
# Creates a virtual display :1 at 1280x800 resolution with 24-bit color.
# This is the "invisible monitor" that all GUI apps will render to.
log_info "Starting Xvfb on display ${DISPLAY_NUM} at ${DISPLAY_RES}..."

Xvfb "${DISPLAY_NUM}" -screen 0 "${DISPLAY_RES}" -ac +extension GLX +render -noreset &
XVFB_PID=$!
sleep 2  # Give Xvfb time to initialize

if kill -0 "$XVFB_PID" 2>/dev/null; then
    log_success "Xvfb started (PID: $XVFB_PID)."
else
    log_error "FATAL: Xvfb failed to start. Cannot proceed without a display."
    exit 1
fi

# --- Step 4b: Start XFCE4 Desktop Environment ---------------------------------
# Launches the lightweight Kali desktop on the virtual display.
# We use startxfce4 in the background so the script continues.
log_info "Launching XFCE4 desktop environment..."

startxfce4 &
XFCE_PID=$!
sleep 3  # Give XFCE time to fully render

if kill -0 "$XFCE_PID" 2>/dev/null; then
    log_success "XFCE4 desktop started (PID: $XFCE_PID)."
else
    log_warn "XFCE4 may have forked to a child process. Continuing..."
fi

# --- Step 4c: Start x11vnc (VNC Server) ----------------------------------------
# Attaches to the Xvfb display and serves it as a VNC stream.
# -forever: Don't exit after the first client disconnects.
# -nopw: No password (security is handled by Docker network isolation).
# -shared: Allow multiple simultaneous viewers.
# -rfbport: The port VNC listens on internally.
log_info "Starting x11vnc VNC server on port ${VNC_PORT}..."

x11vnc \
    -display "${DISPLAY_NUM}" \
    -forever \
    -nopw \
    -shared \
    -rfbport "${VNC_PORT}" \
    -xkb \
    -noxrecord \
    -noxfixes \
    -noxdamage \
    &
X11VNC_PID=$!
sleep 2

if kill -0 "$X11VNC_PID" 2>/dev/null; then
    log_success "x11vnc started (PID: $X11VNC_PID)."
else
    log_error "FATAL: x11vnc failed to start. Desktop will not be accessible."
    exit 1
fi

# --- Step 4d: Start noVNC via websockify (WebSocket Bridge) --------------------
# websockify creates a WebSocket-to-TCP bridge:
#   Browser (WebSocket on :8080) ←→ websockify ←→ x11vnc (TCP on :5901)
#
# This allows the user to view the Kali desktop in any modern web browser
# without installing a VNC client.
log_info "Starting noVNC (websockify) on port ${NOVNC_PORT}..."

websockify \
    --web "${NOVNC_PATH}" \
    "${NOVNC_PORT}" \
    "localhost:${VNC_PORT}" \
    &
NOVNC_PID=$!
sleep 2

if kill -0 "$NOVNC_PID" 2>/dev/null; then
    log_success "noVNC started (PID: $NOVNC_PID)."
else
    log_error "FATAL: noVNC/websockify failed to start."
    exit 1
fi

# ==============================================================================
# BOOT COMPLETE
# ==============================================================================

echo ""
log_success "=================================================="
log_success "  GHOST Workstation is ONLINE"
log_success "=================================================="
log_info    "  Desktop:   http://localhost:${NOVNC_PORT}/vnc.html"
log_info    "  Gateway:   ${GATEWAY_IP} (Tor Transparent Proxy)"
log_info    "  Files:     /root/ghost_files"
log_success "=================================================="
echo ""

# Keep the container alive indefinitely.
# If any background process dies, we catch it and log a warning instead of
# silently failing. The `wait` command blocks until a child process exits.
while true; do
    wait -n 2>/dev/null || true
    sleep 5
done
