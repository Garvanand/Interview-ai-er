@echo off
echo 🚀 Starting Frontend Development Server
echo.

echo 📁 Checking if we're in the right directory...
if not exist "frontend\package.json" (
    echo ❌ Error: Please run this script from the project root directory
    echo    (where you can see the 'frontend' folder)
    pause
    exit /b 1
)

echo ✅ Found frontend directory
echo.

echo 🔧 Setting up environment variables...
if not exist "frontend\.env.local" (
    echo ⚠️  Warning: .env.local file not found
    echo    Please create frontend\.env.local with the contents from env-setup.txt
    echo.
    echo 📋 Creating .env.local from template...
    copy "frontend\env-setup.txt" "frontend\.env.local" >nul 2>&1
    if exist "frontend\.env.local" (
        echo ✅ Created .env.local from template
        echo    Please edit it with your actual Supabase credentials
    ) else (
        echo ❌ Failed to create .env.local
        echo    Please manually create it with the contents from env-setup.txt
    )
    echo.
    pause
) else (
    echo ✅ .env.local file found
)

echo.
echo 📦 Installing dependencies...
cd frontend
call npm install

if %errorlevel% neq 0 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

echo ✅ Dependencies installed
echo.

echo 🌐 Starting development server...
echo    Frontend will be available at: http://localhost:3000
echo    Backend should be running at: http://localhost:5000
echo.
echo    Press Ctrl+C to stop the server
echo.

call npm run dev

pause


