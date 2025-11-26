#!/usr/bin/env python3
"""
Robust local development script for Tribe Backend.

This script handles:
- Virtual environment setup
- Dependency installation
- Database connection checks
- Migration management
- Server startup with proper error handling
"""

import os
import sys
import subprocess
import time
import signal
import platform
from pathlib import Path
from typing import Optional, List

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_colored(message: str, color: str = Colors.RESET):
    """Print colored message."""
    print(f"{color}{message}{Colors.RESET}")


def print_step(step: str):
    """Print a step header."""
    print_colored(f"\n{'='*60}", Colors.CYAN)
    print_colored(f"  {step}", Colors.BOLD + Colors.CYAN)
    print_colored(f"{'='*60}\n", Colors.CYAN)


def print_success(message: str):
    """Print success message."""
    print_colored(f"✓ {message}", Colors.GREEN)


def print_error(message: str):
    """Print error message."""
    print_colored(f"✗ {message}", Colors.RED)


def print_warning(message: str):
    """Print warning message."""
    print_colored(f"⚠ {message}", Colors.YELLOW)


def print_info(message: str):
    """Print info message."""
    print_colored(f"ℹ {message}", Colors.BLUE)


def check_python_version() -> bool:
    """Check if Python version is 3.11+."""
    print_step("Checking Python Version")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print_error(f"Python 3.11+ required. Found {version.major}.{version.minor}.{version.micro}")
        return False
    
    print_success(f"Python {version.major}.{version.minor}.{version.micro} detected")
    return True


def get_venv_path() -> Path:
    """Get virtual environment path."""
    project_root = Path(__file__).parent
    if platform.system() == "Windows":
        return project_root / "venv" / "Scripts"
    return project_root / "venv" / "bin"


def get_python_executable() -> str:
    """Get Python executable path."""
    venv_path = get_venv_path()
    if platform.system() == "Windows":
        return str(venv_path / "python.exe")
    return str(venv_path / "python")


def get_pip_executable() -> str:
    """Get pip executable path."""
    venv_path = get_venv_path()
    if platform.system() == "Windows":
        return str(venv_path / "pip.exe")
    return str(venv_path / "pip")


def setup_venv() -> bool:
    """Create and setup virtual environment."""
    print_step("Setting Up Virtual Environment")
    
    venv_dir = Path(__file__).parent / "venv"
    
    if venv_dir.exists():
        print_info("Virtual environment already exists")
        return True
    
    print_info("Creating virtual environment...")
    try:
        subprocess.run(
            [sys.executable, "-m", "venv", "venv"],
            check=True,
            capture_output=True
        )
        print_success("Virtual environment created")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to create virtual environment: {e}")
        return False


def install_dependencies() -> bool:
    """Install Python dependencies."""
    print_step("Installing Dependencies")
    
    pip_exe = get_pip_executable()
    requirements = Path(__file__).parent / "requirements.txt"
    
    if not requirements.exists():
        print_error(f"requirements.txt not found at {requirements}")
        return False
    
    print_info("Upgrading pip...")
    try:
        subprocess.run(
            [pip_exe, "install", "--upgrade", "pip"],
            check=True,
            capture_output=True
        )
    except subprocess.CalledProcessError:
        print_warning("Failed to upgrade pip, continuing anyway...")
    
    print_info("Installing dependencies from requirements.txt...")
    try:
        result = subprocess.run(
            [pip_exe, "install", "-r", str(requirements)],
            check=True,
            capture_output=False
        )
        print_success("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install dependencies: {e}")
        return False


def check_env_file() -> bool:
    """Check if .env file exists, create from example if not."""
    print_step("Checking Environment Configuration")
    
    env_file = Path(__file__).parent / ".env"
    env_example = Path(__file__).parent / ".env.example"
    
    if env_file.exists():
        print_success(".env file found")
        return True
    
    if env_example.exists():
        print_warning(".env file not found, creating from .env.example...")
        try:
            import shutil
            shutil.copy(env_example, env_file)
            print_success(".env file created from .env.example")
            print_warning("Please update .env with your actual configuration values!")
            return True
        except Exception as e:
            print_error(f"Failed to create .env file: {e}")
            return False
    
    print_error(".env.example not found. Please create .env file manually.")
    return False


def check_database_connection() -> bool:
    """Check if database is accessible."""
    print_step("Checking Database Connection")
    
    python_exe = get_python_executable()
    
    try:
        # Try to import and check database connection
        check_script = """
import asyncio
import sys
from sqlalchemy import text
from app.db.session import engine
from app.core.config import settings

async def check_db():
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        print("Database connection successful")
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(check_db())
    sys.exit(0 if result else 1)
"""
        result = subprocess.run(
            [python_exe, "-c", check_script],
            check=False,
            capture_output=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print_success("Database connection successful")
            return True
        else:
            output = result.stdout.decode() + result.stderr.decode()
            print_error(f"Database connection failed")
            print_info("Make sure PostgreSQL is running and DATABASE_URL is correct in .env")
            print_info(f"Error: {output}")
            return False
    except subprocess.TimeoutExpired:
        print_error("Database connection check timed out")
        return False
    except Exception as e:
        print_warning(f"Could not check database connection: {e}")
        print_info("Continuing anyway... (database will be checked on startup)")
        return True  # Don't fail, let the app handle it


def check_redis_connection() -> bool:
    """Check if Redis is accessible."""
    print_step("Checking Redis Connection")
    
    python_exe = get_python_executable()
    
    try:
        check_script = """
import asyncio
import sys
try:
    import redis.asyncio as redis
    from app.core.config import settings
    
    async def check_redis():
        try:
            r = redis.from_url(settings.redis_url)
            await r.ping()
            await r.close()
            print("Redis connection successful")
            return True
        except Exception as e:
            print(f"Redis connection failed: {e}")
            return False
    
    result = asyncio.run(check_redis())
    sys.exit(0 if result else 1)
except ImportError:
    print("Redis not installed, skipping check")
    sys.exit(0)
"""
        result = subprocess.run(
            [python_exe, "-c", check_script],
            check=False,
            capture_output=True,
            timeout=5
        )
        
        if result.returncode == 0:
            output = result.stdout.decode()
            if "successful" in output:
                print_success("Redis connection successful")
            else:
                print_warning("Redis check skipped (not critical)")
            return True
        else:
            print_warning("Redis connection failed (not critical for basic operation)")
            return True  # Redis is optional for basic operation
    except Exception as e:
        print_warning(f"Could not check Redis: {e}")
        return True  # Don't fail


def run_migrations() -> bool:
    """Run database migrations."""
    print_step("Running Database Migrations")
    
    python_exe = get_python_executable()
    project_root = Path(__file__).parent
    
    # Check if alembic is available
    try:
        result = subprocess.run(
            [python_exe, "-m", "alembic", "current"],
            check=False,
            capture_output=True,
            cwd=project_root,
            timeout=10
        )
        
        print_info("Checking current migration status...")
        
        # Try to upgrade to head
        print_info("Running migrations (alembic upgrade head)...")
        result = subprocess.run(
            [python_exe, "-m", "alembic", "upgrade", "head"],
            check=False,
            capture_output=False,
            cwd=project_root,
            timeout=60
        )
        
        if result.returncode == 0:
            print_success("Migrations completed successfully")
            return True
        else:
            print_warning("Migration command returned non-zero exit code")
            print_info("This might be normal if migrations are already up to date")
            return True  # Don't fail, might just be up to date
    except subprocess.TimeoutExpired:
        print_error("Migration check timed out")
        return False
    except FileNotFoundError:
        print_warning("Alembic not found, skipping migrations")
        print_info("Migrations will be handled by the application on startup")
        return True
    except Exception as e:
        print_warning(f"Could not run migrations: {e}")
        print_info("Continuing anyway...")
        return True


def start_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = True) -> None:
    """Start the FastAPI development server."""
    print_step("Starting Development Server")
    
    python_exe = get_python_executable()
    project_root = Path(__file__).parent
    
    # Change to project root
    os.chdir(project_root)
    
    # Build uvicorn command
    cmd = [
        python_exe, "-m", "uvicorn",
        "app.main:app",
        "--host", host,
        "--port", str(port),
    ]
    
    if reload:
        cmd.append("--reload")
    
    print_info(f"Starting server on http://{host}:{port}")
    print_info("API Documentation: http://localhost:8000/docs")
    print_info("Press Ctrl+C to stop the server\n")
    
    try:
        # Start the server
        process = subprocess.Popen(
            cmd,
            cwd=project_root
        )
        
        # Wait for process
        process.wait()
    except KeyboardInterrupt:
        print_colored("\n\nShutting down server...", Colors.YELLOW)
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        print_success("Server stopped")
        sys.exit(0)
    except Exception as e:
        print_error(f"Failed to start server: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    print_colored("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║           Tribe Backend - Development Server                 ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """, Colors.CYAN + Colors.BOLD)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Run Tribe Backend development server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    parser.add_argument("--skip-checks", action="store_true", help="Skip pre-flight checks")
    parser.add_argument("--skip-migrations", action="store_true", help="Skip database migrations")
    args = parser.parse_args()
    
    # Run pre-flight checks
    if not args.skip_checks:
        checks_passed = True
        
        if not check_python_version():
            checks_passed = False
        
        if not setup_venv():
            checks_passed = False
            sys.exit(1)
        
        if not install_dependencies():
            print_error("Failed to install dependencies")
            print_info("Try running: pip install -r requirements.txt manually")
            checks_passed = False
        
        if not check_env_file():
            checks_passed = False
        
        if not args.skip_migrations:
            if not run_migrations():
                print_warning("Migrations may have failed, but continuing...")
        
        # These are warnings, not failures
        check_database_connection()
        check_redis_connection()
        
        if not checks_passed:
            print_colored("\n" + "="*60, Colors.RED)
            print_error("Some pre-flight checks failed!")
            print_info("You can skip checks with --skip-checks flag")
            print_colored("="*60 + "\n", Colors.RED)
            
            response = input("Continue anyway? (y/N): ").strip().lower()
            if response != 'y':
                sys.exit(1)
    
    # Start the server
    start_server(
        host=args.host,
        port=args.port,
        reload=not args.no_reload
    )


if __name__ == "__main__":
    main()

