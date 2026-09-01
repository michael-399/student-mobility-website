import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Port 5001, not Flask's default 5000: macOS runs an AirPlay Receiver
    # on 5000, which answers on ::1 (where "localhost" resolves first) and
    # returns 403 to anything proxied at it. The container publishes 5001
    # for the same reason, so both ways of running use one port.
    app.run(debug=True, host="127.0.0.1", port=int(os.getenv("PORT", "5001")))
