"""Quick validation script for TPA router"""
import sys
sys.path.insert(0, 'backend')

from fastapi import FastAPI
from routers.tpa_router import router as tpa_router

app = FastAPI()
app.include_router(tpa_router)

print('✅ All TPA endpoints registered:')
for route in app.routes:
    if hasattr(route, 'methods') and hasattr(route, 'path'):
        if '/tpa' in route.path:
            methods = ', '.join(route.methods)
            print(f'   {methods:10} {route.path}')

print(f'\n📊 Total TPA endpoints: {sum(1 for r in app.routes if hasattr(r, "path") and "/tpa" in r.path)}')
print('✅ TPA Router validation complete!')
