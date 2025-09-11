#!/usr/bin/env python3
"""
Deployment script for Mock Interview Platform Backend
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"   Error output: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python 3.8+ required, found {version.major}.{version.minor}")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def create_virtual_environment():
    """Create and activate virtual environment"""
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("🔄 Virtual environment already exists, removing...")
        shutil.rmtree(venv_path)
    
    print("🔄 Creating virtual environment...")
    if not run_command("python -m venv venv", "Creating virtual environment"):
        return False
    
    # Activate virtual environment
    if os.name == 'nt':  # Windows
        activate_script = "venv\\Scripts\\activate"
    else:  # Unix/Linux/Mac
        activate_script = "venv/bin/activate"
    
    print(f"✅ Virtual environment created at {venv_path}")
    print(f"💡 To activate: {activate_script}")
    return True

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    
    # Upgrade pip first
    if not run_command("python -m pip install --upgrade pip", "Upgrading pip"):
        return False
    
    # Install requirements
    if not run_command("pip install -r requirements.txt", "Installing requirements"):
        return False
    
    print("✅ Dependencies installed successfully")
    return True

def check_environment_variables():
    """Check if required environment variables are set"""
    print("🔧 Checking environment variables...")
    
    required_vars = ['SUPABASE_URL', 'SUPABASE_KEY', 'GEMINI_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("💡 Please set these variables in your .env file or environment")
        return False
    
    print("✅ All required environment variables are set")
    return True

def run_tests():
    """Run the test suite"""
    print("🧪 Running tests...")
    
    if not run_command("python test_comprehensive.py", "Running comprehensive tests"):
        print("⚠️  Tests failed, but continuing with deployment...")
        return True  # Continue even if tests fail
    
    print("✅ Tests completed")
    return True

def create_logs_directory():
    """Create logs directory"""
    print("📁 Creating logs directory...")
    
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    print("✅ Logs directory created")
    return True

def create_startup_scripts():
    """Create startup scripts for different platforms"""
    print("🚀 Creating startup scripts...")
    
    # Windows batch file
    if os.name == 'nt':
        with open("start_server.bat", "w") as f:
            f.write("@echo off\n")
            f.write("echo Starting Mock Interview Platform Backend...\n")
            f.write("python app.py\n")
            f.write("pause\n")
    
    # Unix/Linux/Mac shell script
    else:
        with open("start_server.sh", "w") as f:
            f.write("#!/bin/bash\n")
            f.write("echo 'Starting Mock Interview Platform Backend...'\n")
            f.write("python app.py\n")
        
        # Make executable
        os.chmod("start_server.sh", 0o755)
    
    print("✅ Startup scripts created")
    return True

def create_docker_files():
    """Create Docker configuration files"""
    print("🐳 Creating Docker configuration...")
    
    # Dockerfile
    dockerfile_content = """FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:5000/api/health || exit 1

# Run the application
CMD ["python", "app.py"]
"""
    
    with open("Dockerfile", "w") as f:
        f.write(dockerfile_content)
    
    # .dockerignore
    dockerignore_content = """venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
.env
*.log
logs/
.git/
.gitignore
README.md
*.md
"""
    
    with open(".dockerignore", "w") as f:
        f.write(dockerignore_content)
    
    # docker-compose.yml
    docker_compose_content = """version: '3.8'

services:
  backend:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - FLASK_SECRET_KEY=${FLASK_SECRET_KEY}
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
"""
    
    with open("docker-compose.yml", "w") as f:
        f.write(docker_compose_content)
    
    print("✅ Docker configuration created")
    return True

def create_systemd_service():
    """Create systemd service file for Linux"""
    if os.name == 'nt':  # Skip on Windows
        return True
    
    print("🔧 Creating systemd service file...")
    
    service_content = """[Unit]
Description=Mock Interview Platform Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/your/app
Environment=PATH=/path/to/your/app/venv/bin
ExecStart=/path/to/your/app/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    with open("mock-interview-backend.service", "w") as f:
        f.write(service_content)
    
    print("✅ Systemd service file created")
    print("💡 Remember to update the paths in the service file")
    return True

def main():
    """Main deployment function"""
    print("🚀 Mock Interview Platform Backend - Deployment Script")
    print("=" * 60)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create virtual environment
    if not create_virtual_environment():
        print("❌ Failed to create virtual environment")
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    # Check environment variables
    if not check_environment_variables():
        print("❌ Environment variables not properly configured")
        print("💡 Please create a .env file with required variables")
        sys.exit(1)
    
    # Run tests
    run_tests()
    
    # Create logs directory
    create_logs_directory()
    
    # Create startup scripts
    create_startup_scripts()
    
    # Create Docker files
    create_docker_files()
    
    # Create systemd service (Linux only)
    create_systemd_service()
    
    print("\n" + "=" * 60)
    print("🎉 Deployment completed successfully!")
    print("\n📋 Next steps:")
    print("   1. Activate virtual environment:")
    if os.name == 'nt':
        print("      venv\\Scripts\\activate")
    else:
        print("      source venv/bin/activate")
    
    print("   2. Start the server:")
    if os.name == 'nt':
        print("      start_server.bat")
    else:
        print("      ./start_server.sh")
    
    print("\n🐳 Docker deployment:")
    print("   docker-compose up --build")
    
    print("\n🔧 Production deployment:")
    print("   - Update systemd service file paths")
    print("   - Copy service file to /etc/systemd/system/")
    print("   - Enable and start service")
    
    print("\n📚 Documentation:")
    print("   - README.md for detailed setup instructions")
    print("   - API documentation available at /api/health when running")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
