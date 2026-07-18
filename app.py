from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


SERVER_DIR = Path(__file__).resolve().parent / "server"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

spec = spec_from_file_location("cardiosense_server_app", SERVER_DIR / "app.py")
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load server/app.py")

module = module_from_spec(spec)
spec.loader.exec_module(module)
app = module.app


if __name__ == "__main__":
    app.run(debug=True)
