#!/bin/bash
#
# GhostConnect Quick Installer
# Run with: sudo bash install.sh
#

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${GREEN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║           GhostConnect Installation Script                    ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}[✗] This script must be run as root${NC}"
   echo -e "${YELLOW}[!] Please run: sudo bash install.sh${NC}"
   exit 1
fi

echo -e "${GREEN}[✓] Root privileges confirmed${NC}"

# Check if python3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[✗] Python3 is not installed${NC}"
    echo -e "${CYAN}[*] Installing Python3...${NC}"
    apt update && apt install -y python3 python3-pip
else
    echo -e "${GREEN}[✓] Python3 found: $(python3 --version)${NC}"
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}[!] pip3 not found, installing...${NC}"
    apt install -y python3-pip
fi

echo -e "${GREEN}[✓] pip3 found${NC}"

# Install Python dependencies
echo -e "${CYAN}[*] Installing Python dependencies...${NC}"
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo -e "${GREEN}[✓] Python dependencies installed${NC}"
else
    echo -e "${RED}[✗] Failed to install Python dependencies${NC}"
    exit 1
fi

# Make the script executable
chmod +x ghostconnect.py
echo -e "${GREEN}[✓] Made ghostconnect.py executable${NC}"

# Create symbolic link for easy access (optional)
if [ ! -f "/usr/local/bin/ghostconnect" ]; then
    ln -s "$(pwd)/ghostconnect.py" /usr/local/bin/ghostconnect
    echo -e "${GREEN}[✓] Created symbolic link: /usr/local/bin/ghostconnect${NC}"
    echo -e "${CYAN}[*] You can now run 'sudo ghostconnect' from anywhere${NC}"
fi

echo -e "\n${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              Installation Complete!                           ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"

echo -e "\n${CYAN}Quick Start:${NC}"
echo -e "  1. Run the tool: ${YELLOW}sudo python3 ghostconnect.py${NC}"
echo -e "     Or simply:    ${YELLOW}sudo ghostconnect${NC}"
echo -e "\n  2. Wait for Tor to bootstrap"
echo -e "  3. Browse anonymously in the launched Firefox"
echo -e "  4. Press CTRL+C when done to clean up\n"

echo -e "${YELLOW}[!] Remember: This tool aids privacy but is not foolproof${NC}"
echo -e "${YELLOW}[!] Always follow security best practices${NC}\n"
