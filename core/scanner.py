# core/scanner.py
import clr
import os
import sys
import io
import threading
from PIL import Image
from System import Activator, Type
from System.Threading import CancellationTokenSource


# Locate ScannerEngine.dll in both Development and PyInstaller EXE
if getattr(sys, "frozen", False):
    # Running from PyInstaller one-file EXE
    dll_path = os.path.join(sys._MEIPASS, "ScannerEngine.dll")
else:
    # Running from source code
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dll_path = os.path.join(base_dir, "libs", "ScannerEngine.dll")

if not os.path.exists(dll_path):
    raise FileNotFoundError(
        f"ScannerEngine.dll not found at {dll_path}"
    )

clr.AddReference(dll_path)

class Scanner:
    def __init__(self, settings):
        self.settings = settings
        self.available = False
        self.devices = []
        self.is_scanning = False
        self.cancel_source = None
        self._init_complete = False

        # Create the C# object
        scanner_type = Type.GetType("ScannerManager, ScannerEngine")
        if scanner_type is None:
            raise Exception("Cannot load ScannerManager from ScannerEngine.dll")
        self.manager = Activator.CreateInstance(scanner_type)

    # In core/scanner.py, modify initialize method to timeout after 5 seconds
    def initialize(self, callback):
        def task():
            try:
                # Try to load devices quickly
                self.refresh_devices()
                self.available = True
                callback(True, None)
            except Exception as e:
                # Timeout or error
                callback(False, str(e))
        thread = threading.Thread(target=task, daemon=True)
        thread.start()

    def refresh_devices(self):
        try:
            devices = self.manager.GetDevices()
            self.devices = [str(d) for d in devices] if devices else []
        except Exception as e:
            self.devices = []
            raise e

    def get_devices(self):
        return self.devices

    def select_device(self, index):
        try:
            self.manager.SelectDevice(int(index))
            return True
        except:
            return False

    def select_device_by_name(self, name):
        if name in self.devices:
            idx = self.devices.index(name)
            return self.select_device(idx)
        return False

    def is_busy(self):
        try:
            return bool(self.manager.IsBusy())
        except:
            return False

    def scan_async(self, progress_callback=None, result_callback=None,
                   error_callback=None, status_callback=None):
        if self.is_scanning:
            if error_callback:
                error_callback("Scan already in progress")
            return

        self.is_scanning = True
        self.cancel_source = CancellationTokenSource()
        token = self.cancel_source.Token

        def worker():
            try:
                if status_callback:
                    status_callback("INITIALIZING")
                data = self.manager.Scan(0, token)
                if data is None:
                    if status_callback:
                        status_callback("CANCELLED")
                    if error_callback:
                        error_callback("Scan cancelled")
                    return
                if status_callback:
                    status_callback("PROCESSING")
                img_bytes = bytes(bytearray(data))
                img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                if result_callback:
                    result_callback(img)
                if status_callback:
                    status_callback("DONE")
            except Exception as e:
                if error_callback:
                    error_callback(str(e))
            finally:
                self.is_scanning = False
                self.cancel_source = None

        threading.Thread(target=worker, daemon=True).start()

    def cancel_scan(self):
        if self.cancel_source:
            self.cancel_source.Cancel()
        try:
            self.manager.ForceAbort()
        except:
            pass
        self.is_scanning = False

    def check_status(self):
        return {"online": self.available, "busy": self.is_scanning, "message": ""}