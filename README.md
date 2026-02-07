# GhostConnect - Anonymous Browsing Kill Switch

A robust, automated CLI tool for creating a secure anonymous browsing environment on Kali Linux using Tor, ProxyChains, and Firefox.

## Features

- **Automated Setup**: Checks and installs all dependencies (Tor, ProxyChains4, Firefox)
- **Intelligent Configuration**: Automatically configures ProxyChains for optimal security
- **Isolated Browser Profile**: Creates a dedicated Firefox profile with hardened privacy settings
- **DNS Leak Prevention**: Disables WebRTC, IPv6, and enforces DNS through Tor
- **Bootstrap Detection**: Waits for Tor to establish circuits before launching browser
- **Clean Kill Switch**: CTRL+C cleanly terminates everything and normalizes connection
- **Professional UI**: Rich terminal interface with progress indicators and status messages

## Architecture

The tool follows a modular design with three main phases:

1. **Check & Fix Phase**: Verifies root privileges, installs dependencies, configures ProxyChains
2. **Launch Phase**: Starts Tor, waits for bootstrap, launches isolated Firefox
3. **Cleanup Phase**: Terminates browser, stops Tor, restores configurations

## Prerequisites

- **Kali Linux** (or any Debian-based Linux distribution)
- **Python 3.7+**
- **Root/sudo privileges**

## Installation

1. Clone or download this tool:
```bash
cd /opt
git clone <your-repo> GhostConnect
cd GhostConnect
```

2. Install Python dependencies:
```bash
pip3 install -r requirements.txt
```

3. Make the script executable:
```bash
chmod +x ghostconnect.py
```

## Usage

Run the tool with sudo:

```bash
sudo python3 ghostconnect.py
```

### What Happens

1. **Root Check**: Ensures you have proper privileges
2. **Dependency Installation**: Auto-installs Tor, ProxyChains4, and Firefox if missing
3. **Configuration**:
   - Backs up original ProxyChains config
   - Configures strict chain mode with DNS proxying
   - Creates isolated Firefox profile "GhostProfile"
   - Injects privacy settings (disables WebRTC, IPv6, telemetry, etc.)
4. **Tor Launch**: Starts Tor service and waits for circuit establishment
5. **Browser Launch**: Opens Firefox through ProxyChains in anonymous mode
6. **Active Monitoring**: Displays status and waits for user action
7. **Clean Exit**: Press CTRL+C to cleanly shut down everything

### Privacy Settings Applied

The tool automatically configures Firefox with:

- **WebRTC disabled** - Prevents IP leaks through WebRTC
- **IPv6 disabled** - Forces IPv4 to prevent IPv6 leaks
- **Direct proxy mode** - Lets ProxyChains handle routing
- **Fingerprinting resistance** - Reduces browser fingerprinting
- **First-party isolation** - Isolates cookies per domain
- **Telemetry disabled** - Blocks all Firefox telemetry
- **DNS prefetching disabled** - Prevents DNS leaks
- **Clear on shutdown** - Removes traces after closing

## Security Notes

### What This Tool Does

- Routes all Firefox traffic through Tor network
- Prevents DNS leaks
- Disables WebRTC IP leaks
- Creates isolated browsing environment
- Cleans up after itself

### What This Tool Does NOT Do

- This is NOT a silver bullet for complete anonymity
- Does not protect against:
  - Browser fingerprinting (partially mitigated)
  - Login-based tracking (if you log into accounts)
  - Advanced persistent threats
  - Physical attacks or malware
- Does not encrypt traffic beyond Tor exit nodes
- Does not guarantee protection if you reveal identifying information

### Best Practices

1. **Never log into personal accounts** while in Ghost Mode
2. **Don't download files** that could contain identifying metadata
3. **Verify your IP** at https://check.torproject.org
4. **Keep Tor Browser updated** for latest security patches
5. **Consider Tails OS** for higher security requirements
6. **Don't mix** anonymous and non-anonymous browsing

## Troubleshooting

### Tor won't start
```bash
# Check Tor status
sudo service tor status

# View Tor logs
sudo tail -f /var/log/tor/log

# Restart manually
sudo service tor restart
```

### Firefox won't launch
```bash
# Check if Firefox is already running
ps aux | grep firefox

# Kill existing instances
pkill -9 firefox

# Verify ProxyChains config
cat /etc/proxychains4.conf
```

### Port 9050 already in use
```bash
# Find what's using the port
sudo netstat -tulpn | grep 9050

# Stop conflicting service
sudo service tor stop
```

### Profile creation fails
```bash
# Check Firefox profile directory
ls -la ~/.mozilla/firefox/

# Manually create profile
firefox -CreateProfile GhostProfile

# Check profiles
firefox -P
```

## File Structure

```
GhostConnect/
├── ghostconnect.py       # Main tool
├── requirements.txt      # Python dependencies
├── README.md            # This file
└── LICENSE              # License file
```

## Configuration Files Modified

- **/etc/proxychains4.conf** - ProxyChains configuration (backed up to .ghost.bak)
- **~/.mozilla/firefox/[profile]/user.js** - Firefox privacy settings

## Technical Details

### ProxyChains Configuration

```
strict_chain              # All proxies must be online
proxy_dns                 # DNS requests through proxy
socks5 127.0.0.1 9050    # Tor SOCKS5 proxy
```

### Tor Service

- **SOCKS Port**: 9050
- **Control Port**: 9051 (if enabled)
- **Service**: systemd service `tor`

### Signal Handling

The tool properly handles:
- SIGINT (CTRL+C)
- SIGTERM (kill)

Both trigger clean shutdown sequence.

## License

This tool is provided for educational and authorized security testing purposes only.

## Disclaimer

**IMPORTANT**: This tool is designed for:
- Legitimate privacy protection
- Authorized security research
- Educational purposes
- Penetration testing with proper authorization

**DO NOT USE** for:
- Illegal activities
- Unauthorized access
- Malicious purposes
- Evading law enforcement

The author assumes no liability for misuse of this tool. Always comply with applicable laws and regulations.

## Contributing

Contributions are welcome! Please ensure:
- Code follows existing style
- Security best practices maintained
- Documentation updated
- Testing on Kali Linux

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check troubleshooting section above
- Review Tor Project documentation

## Credits

Built with:
- [Tor Project](https://www.torproject.org/)
- [ProxyChains](https://github.com/haad/proxychains)
- [Firefox](https://www.mozilla.org/firefox/)
- [Rich](https://github.com/Textualize/rich) - Terminal formatting
- [Colorama](https://github.com/tartley/colorama) - Cross-platform colors

---

**Stay Anonymous. Stay Safe. Stay Legal.**

🔒 Ghost Mode Activated
