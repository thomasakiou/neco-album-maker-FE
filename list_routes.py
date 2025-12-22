from app.main import app
for route in app.routes:
    print(f"Path: {route.path}, Methods: {getattr(route, 'methods', 'N/A')}")
