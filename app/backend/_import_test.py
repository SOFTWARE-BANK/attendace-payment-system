import sys
import traceback

try:
    import core.bootstrap_env
    print("OK")
except Exception:
    print("IMPORT_FAILED")
    traceback.print_exc()
    sys.exit(1)
