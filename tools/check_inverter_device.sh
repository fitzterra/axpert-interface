#!/usr/bin/env bash
#
# Reboot the container if the inverter device entry goes away.
#
# This is specific to my environment where I run this axpert monitor in a
# dedicated Incus container with the inverter device passed through as a
# character device from the host to the container.
#
# It seems every night at a specific time this event occurs for the USB device
# (from dmesg on the host):
#
# [Sat Mar 15 02:21:55 2025] usb usb1-port9: disabled by hub (EMI?), re-enabling...
# [Sat Mar 15 02:21:55 2025] usb 1-9: USB disconnect, device number 24
# [Sat Mar 15 02:22:01 2025] usb 1-9: new low-speed USB device number 25 using xhci_hcd
# [Sat Mar 15 02:22:01 2025] usb 1-9: New USB device found, idVendor=0665, idProduct=5161, bcdDevice= 0.02
# [Sat Mar 15 02:22:01 2025] usb 1-9: New USB device strings: Mfr=3, Product=1, SerialNumber=0
# [Sat Mar 15 02:22:01 2025] hid-generic 0003:0665:5161.0017: hiddev0,hidraw0: USB HID v1.11 Device [HID 0665:5161] on usb-0000:00:14.0-9/input0
# 
# As soon as this happens the device becomes unavailable in the container. I'm
# not sure if this from the inverted disconnecting or the kernel doing
# something. Trying to figure out the reason seems more difficult than just
# writing a quick tool to monitor for this sitution and restart the container.
#
# This script will be started every odd minute (the axpert command to fetch
# inverter state run every even minute), and check to see if the /dev/hidAxpert
# device exists. If not, and we have not rebooted in the last X minutes, it
# will reboot the container.
#
# The reason to check for the last time we rebooted is so we do not get in a
# state where there is a real issue with the inverter device and we reboot
# every 2 minutes.

DEV=/dev/hidAxpert
MIN_UPTIME=$((2*3600))  # Minimum uptime in seconds (2 hours)

# Check if the device is there and is a character device.
if [[ -c $DEV ]]; then
    # Now check if we can open it by using exec to allocate a new test file
    # descriptor for reading from the file
    if exec 3<"$DEV"; then
        # All good, we can close the test fd and then exit
        exec 3<&-
        exit 0
    fi
fi

# If we have not been up for longer than MIN_UPTIME, we can not reboot yet
if [ $(($(date +%s) - $(date +%s -d "$(uptime -s)"))) -lt $MIN_UPTIME ]; then
    echo "Device $DEV is not available, but not rebooting since uptime is less than ${MIN_UPTIME}s"
    # We exit with success so as not to indicate this as an error to cron
    exit 0
fi

# Echo output to standard out so cron picks this up and send a notification
# email, and also output to the reboot log file.
echo "$(date): The inverter device $DEV is not available. "\
     "Scheduling a reboot in 1 minute to attempt recovery." | sudo tee -a /var/log/container-reboot.log

# Schedule reboot after 1 minute using 'at' to allow cron to send the email
echo "sudo /sbin/reboot" | at now + 1 minute


