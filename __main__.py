import argparse

from .web.app import HOST, PORT, run


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DevSecOps Copilot web sunucusu")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()
    run(args.host, args.port)
