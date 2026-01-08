#!/bin/bash

echo "════════════════════════════════════════════════"
echo "  POLONO PL60 Thermal Printer Setup"
echo "════════════════════════════════════════════════"
echo ""

# Add printer to CUPS
echo "📝 Adding POLONO PL60 to CUPS..."
echo "   Trying IPP Everywhere driver..."

sudo lpadmin -p POLONO_PL60 \
  -v "usb://POLONO/PL60?serial=PL600021161541" \
  -m everywhere \
  -E

if [ $? -ne 0 ]; then
  echo "   IPP Everywhere failed, trying Generic PostScript..."
  sudo lpadmin -p POLONO_PL60 \
    -v "usb://POLONO/PL60?serial=PL600021161541" \
    -m drv:///sample.drv/generic.ppd \
    -E
fi

if [ $? -eq 0 ]; then
  echo "✓ Printer added successfully"
else
  echo "❌ Failed to add printer"
  echo ""
  echo "📱 Alternative: Add via System Settings"
  echo "   1. Open System Settings → Printers & Scanners"
  echo "   2. Click '+' to add the POLONO PL60"
  echo "   3. Select it from the list and add"
  echo ""
  exit 1
fi

# Set as default printer
echo ""
echo "📌 Setting as default printer..."
sudo lpoptions -d POLONO_PL60

if [ $? -eq 0 ]; then
  echo "✓ Default printer set"
else
  echo "⚠ Could not set as default (non-critical)"
fi

# Configure printer options for labels
echo ""
echo "⚙️  Configuring printer options..."
# Set media size to 2" x 1" (51x25mm)
sudo lpadmin -p POLONO_PL60 -o media=Custom.51x25mm

# Verify installation
echo ""
echo "════════════════════════════════════════════════"
echo "  Printer Status"
echo "════════════════════════════════════════════════"
lpstat -p POLONO_PL60
echo ""
echo "Default printer: $(lpstat -d)"
echo ""
echo "✅ Setup complete!"
echo ""
echo "To test the printer, run:"
echo "  echo 'Test' | lp -d POLONO_PL60"
echo ""
