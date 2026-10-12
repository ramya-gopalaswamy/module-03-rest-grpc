import sys
from pathlib import Path

_SERVICE_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SERVICE_DIR.parent


def load_grpcio():
    """Import grpcio when this directory is also named grpc."""
    sys.path = [
        entry
        for entry in sys.path
        if Path(entry or ".").resolve() not in {_SERVICE_DIR, _PROJECT_ROOT}
    ]
    current = sys.modules.get("grpc")
    current_file = getattr(current, "__file__", None)
    if current is not None and current_file:
        if Path(current_file).resolve().parent == _SERVICE_DIR:
            sys.modules.pop("grpc", None)
            for name in list(sys.modules):
                if name.startswith("grpc."):
                    sys.modules.pop(name, None)

    import grpc

    service_dir = str(_SERVICE_DIR)
    if service_dir not in sys.path:
        sys.path.insert(0, service_dir)
    return grpc
