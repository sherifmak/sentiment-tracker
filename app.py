"""Sentiment Trading Tracker — Dash application entry point."""

from dash import Dash
import dash_bootstrap_components as dbc

from dashboard.layout import create_layout
from dashboard.callbacks import register_callbacks

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    title="Sentiment Tracker",
    update_title="Loading...",
)

app.layout = create_layout()
register_callbacks(app)

server = app.server  # For production WSGI deployment

if __name__ == "__main__":
    print("\n  Sentiment Tracker starting...")
    print("  Dashboard: http://127.0.0.1:8050\n")
    app.run(debug=True, host="0.0.0.0", port=8050)
