# GhostConnect Quick Reference

## Quick Start Commands

```bash
# Installation
sudo bash install.sh

# Run system verification
sudo python3 test_setup.py

# Launch GhostConnect
sudo python3 ghostconnect.py

# Or if symbolic link created
sudo ghostconnect
```

## Command Flow

```
Root Check → Install Dependencies → Configure ProxyChains
    → Create Firefox Profile → Start Tor → Wait for Bootstrap
    → Launch Firefox → [Browse Anonymously] → CTRL+C → Clean Shutdown
```

## Key Features

| Feature | Description |
|---------|-------------|
| Auto-Install | Installs Tor, ProxyChains4, Firefox automatically |
| Config Backup | Backs up original ProxyChains config |
| Privacy Hardening | 20+ Firefox privacy settings applied |
| WebRTC Leak Protection | Disables WebRTC to prevent IP leaks |
| DNS Leak Protection | Routes DNS through Tor |
| Bootstrap Detection | Waits for Tor circuits before launching |
| Clean Exit | CTRL+C safely terminates everything |

## Privacy Settings Applied

```javascript
// WebRTC disabled
media.peerconnection.enabled = false

// IPv6 disabled
network.dns.disableIPv6 = true

// Fingerprinting resistance
privacy.resistFingerprinting = true

// First party isolation
privacy.firstparty.isolate = true

// And 15+ more settings...
```

## File Locations

| File | Location | Purpose |
|------|----------|---------|
| Main Script | `./ghostconnect.py` | Main tool executable |
| ProxyChains Config | `/etc/proxychains4.conf` | Routing configuration |
| Config Backup | `/etc/proxychains4.conf.ghost.bak` | Original config backup |
| Firefox Profile | `~/.mozilla/firefox/*.GhostProfile/` | Isolated browser profile |
| Privacy Settings | `~/.mozilla/firefox/*.GhostProfile/user.js` | Firefox privacy config |

## Tor Configuration

```
Service: tor
SOCKS Port: 9050
Protocol: SOCKS5
```

## Verification Checklist

Before first use, verify:

- [ ] Running on Kali Linux (or Debian-based system)
- [ ] Have root/sudo access
- [ ] Python 3.7+ installed
- [ ] Internet connection available
- [ ] No VPN conflicts (disable VPN before using Tor)

## Testing Your Setup

1. **Run verification script**:
   ```bash
   sudo python3 test_setup.py
   ```

2. **Launch GhostConnect**:
   ```bash
   sudo python3 ghostconnect.py
   ```

3. **Check your IP in Firefox**:
   - Visit: https://check.torproject.org
   - Should show: "Congratulations. This browser is configured to use Tor."

4. **Test for leaks**:
   - WebRTC: https://browserleaks.com/webrtc
   - DNS: https://www.dnsleaktest.com
   - IP: https://ipleak.net

## Common Operations

### Clean Shutdown
```
Press CTRL+C in terminal
```

### Manual Tor Restart
```bash
sudo service tor restart
```

### View Tor Logs
```bash
sudo tail -f /var/log/tor/log
```

### Kill All Firefox Instances
```bash
sudo pkill -9 firefox
```

### Check Tor Port Status
```bash
netstat -tulpn | grep 9050
```

### Restore Original ProxyChains Config
```bash
sudo cp /etc/proxychains4.conf.ghost.bak /etc/proxychains4.conf
```

## Troubleshooting Quick Fixes

| Problem | Solution |
|---------|----------|
| "Not running as root" | Use `sudo` before command |
| Tor won't start | `sudo service tor restart` |
| Port 9050 in use | `sudo service tor stop && sudo service tor start` |
| Firefox won't launch | `sudo pkill -9 firefox`, then retry |
| Config errors | Delete `~/.mozilla/firefox/*.GhostProfile/` and rerun |
| Slow connection | Normal for Tor; wait for circuits to optimize |

## Security Best Practices

### DO:
- ✓ Verify you're using Tor at https://check.torproject.org
- ✓ Keep system and Tor updated
- ✓ Close all other applications
- ✓ Use HTTPS websites when possible
- ✓ Clear cookies/cache between sessions

### DON'T:
- ✗ Log into personal accounts
- ✗ Download files with identifying metadata
- ✗ Maximize Firefox window (fingerprinting)
- ✗ Enable plugins/extensions
- ✗ Mix anonymous and normal browsing
- ✗ Use torrents over Tor

## Performance Tips

1. **First connection is slowest** - Tor needs to build circuits
2. **Patience** - Tor routing adds latency
3. **New circuit** - Close/reopen browser if very slow
4. **Avoid multimedia** - Streaming may be slow
5. **Onion sites** - Often faster than clearnet through Tor

## Exit Procedure

1. Close Firefox browser window **OR** Press CTRL+C
2. Tool automatically:
   - Terminates Firefox process
   - Stops Tor service
   - Restores ProxyChains config
   - Displays "Ghost Mode Deactivated"

## Advanced Usage

### Custom Tor Config
Edit `/etc/tor/torrc` before running GhostConnect

### Add Tor Bridges
If Tor is blocked in your country:
```bash
# Edit /etc/tor/torrc
UseBridges 1
Bridge obfs4 [bridge address]
```

### Multiple Circuits
Close and reopen Firefox to get new circuit/IP

### Check Current IP
```bash
# While Tor is running
proxychains4 curl https://check.torproject.org/api/ip
```

## Uninstallation

```bash
# Remove symbolic link
sudo rm /usr/local/bin/ghostconnect

# Remove ProxyChains backup
sudo rm /etc/proxychains4.conf.ghost.bak

# Delete Firefox profile (optional)
rm -rf ~/.mozilla/firefox/*.GhostProfile

# Uninstall packages (optional)
sudo apt remove tor proxychains4
```

## Resources

- **Tor Project**: https://www.torproject.org
- **Tor Browser Manual**: https://tb-manual.torproject.org
- **ProxyChains**: https://github.com/haad/proxychains
- **Check Tor**: https://check.torproject.org
- **Leak Tests**: https://ipleak.net

## Support

For issues:
1. Run `sudo python3 test_setup.py`
2. Check `/var/log/tor/log`
3. Verify dependencies installed
4. Read troubleshooting section

---

**Remember**: Anonymity is a practice, not a product. Stay vigilant.
