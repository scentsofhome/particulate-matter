# boot.py -- runs on boot-up
import network
import time
import webrepl

print("Initializing local Wi-Fi network...")

# 1. Disable the client (Station) interface to keep things clean
wlan_sta = network.WLAN(network.STA_IF)
wlan_sta.active(False)
time.sleep(0.5)

# 2. Enable the Access Point (Hosting) interface
wlan_ap = network.WLAN(network.AP_IF)
wlan_ap.active(True)

# 3. Configure your local network name and password
# Note: Password must be at least 8 characters long!
AP_SSID = "ESP32-Sensor-Network"
AP_PASSWORD = "tame"

wlan_ap.config(essid=AP_SSID, password=AP_PASSWORD)

# Give the hardware a brief moment to spin up the network radio
time.sleep(1)

# Confirm network details in the terminal
print(f"Network '{AP_SSID}' is now broadcasting!")
print("Board IP Address (Gateway):", wlan_ap.ifconfig()[0]) # This will be 192.168.4.1

# 4. Start the wireless terminal listener for your web app
webrepl.start()