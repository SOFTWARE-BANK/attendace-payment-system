import sys
import traceback

try:
    import services.hikvision
    print("HIKVISION_OK")
except Exception:
    print("HIKVISION_IMPORT_FAILED")
    traceback.print_exc()
    sys.exit(1)
