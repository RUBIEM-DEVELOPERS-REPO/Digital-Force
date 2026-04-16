@echo off
echo Starting Digital Force frontend...
cd /d "d:\KASHIRI BRIGHTON\BUSINESS\AiiA\Digital Force\frontend"

if not exist node_modules (
    echo Installing npm packages...
    npm install
)

echo.
echo Clearing Next.js cache to prevent proxy hangs...
if exist .next rmdir /s /q .next

echo.
echo Starting Next.js dev server on port 3000 (Webpack mode)...
set NODE_OPTIONS=--max-old-space-size=3072
npm run dev -- --webpack
