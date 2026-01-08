# Upscaled Print Agent (macOS, unsigned)

This creates an unsigned macOS installer (.pkg) for the print agent.

## Build

```bash
bash deploy/print_agent/macos/build_macos_print_agent.sh
```

Set `PRINT_AGENT_ARCH=x64` to build for Intel Macs.

Output:

```
Upscaled_inv_processing/ui/downloads/upscaled-print-agent-macos.pkg
```

## Install (unsigned)

1) Double-click the .pkg
2) If macOS blocks it, go to **System Settings → Privacy & Security** and click **Open Anyway**
3) Confirm the install and run once

The installer installs:
- `/usr/local/bin/upscaled-print-agent`
- `/Library/LaunchAgents/com.upscaled.printagent.plist` (auto-starts on login)

Check logs:
- `/tmp/upscaled-print-agent.log`
- `/tmp/upscaled-print-agent.err`

## Uninstall

```bash
sudo launchctl unload /Library/LaunchAgents/com.upscaled.printagent.plist
sudo rm /Library/LaunchAgents/com.upscaled.printagent.plist
sudo rm /usr/local/bin/upscaled-print-agent
```
