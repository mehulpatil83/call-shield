"""Start call-shield locally:  python -m app.run   then open http://127.0.0.1:8000
The server always binds to 127.0.0.1 only. For call mode a tunnel program (cloudflared) connects to it locally and gives
the phone an https address; see tools/start_demo.bat."""
import argparse
import threading
import webbrowser

import uvicorn

from .backend.main import FRONTEND_DIST, create_app


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--public-url", default=None,
                    help="https address of your tunnel (optional: call mode can also detect it or you can paste it in the page)")
    a = ap.parse_args()
    if not (FRONTEND_DIST / "index.html").exists():
        print("Note: the web page is not built yet (app/frontend/dist is missing).\n"
              "The API still works at /api/docs. To build the page: cd app\\frontend, npm install, npm run build.")
    url = f"http://127.0.0.1:{a.port}"
    if not a.no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    print(f"call-shield running at {url}  (Ctrl+C to stop)")
    uvicorn.run(create_app(public_url=a.public_url), host="127.0.0.1", port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
