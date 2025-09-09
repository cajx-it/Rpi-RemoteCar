import time
import pexpect

class BluetoothctlError(Exception):
    """This exception is raised when bluetoothctl fails to start."""
    pass

class BluetoothctlInteract:
    def __init__(self, mac_address):
        self.mac = mac_address
        self.child = pexpect.spawn("bluetoothctl", echo=False)
        self.setup_bluetooth()

    def setup_bluetooth(self):
        """Initial Bluetooth setup commands."""
        print("Setting up bluetooth...")
        self.child.sendline("power on")
        self.child.sendline("agent on")
        self.child.sendline("default-agent")
        self.child.sendline(f"trust {self.mac}")
        time.sleep(1)
        self.connect_device()

    def connect_device(self):
        """Attempt to connect to the Bluetooth device."""
        print(f"[CONNECTING] to {self.mac}...")
        self.child.sendline(f"connect {self.mac}")


if __name__ == "__main__":
    mac = "C1:87:4B:87:B7:0C"  # Replace with your device's MAC
    bt = BluetoothctlInteract(mac)
    
