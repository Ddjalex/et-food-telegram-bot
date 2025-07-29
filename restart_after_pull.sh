#!/bin/bash
# Restart Replit Environment After Git Pull
# This script ensures the environment uses the latest files after pulling from GitHub

set -e

echo "🔄 Restarting Replit environment after Git pull..."

# Function to stop running processes
stop_processes() {
    echo "🛑 Stopping running processes..."
    
    # Kill any Python processes (except this script)
    pkill -f "python.*app" 2>/dev/null || true
    pkill -f "gunicorn" 2>/dev/null || true
    pkill -f "flask" 2>/dev/null || true
    
    # Wait a moment for processes to stop
    sleep 2
    
    echo "✅ Processes stopped"
}

# Function to clear Python cache
clear_cache() {
    echo "🧹 Clearing Python cache..."
    
    # Remove all Python cache files
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    # Clear any application-specific cache
    rm -rf .cache/ 2>/dev/null || true
    rm -rf instance/ 2>/dev/null || true
    
    echo "✅ Cache cleared"
}

# Function to verify file integrity
verify_files() {
    echo "🔍 Verifying file integrity after pull..."
    
    # Check that key files exist
    if [ ! -f "app.py" ]; then
        echo "❌ Critical file missing: app.py"
        exit 1
    fi
    
    if [ ! -f "main.py" ]; then
        echo "❌ Critical file missing: main.py"
        exit 1
    fi
    
    if [ ! -f "models.py" ]; then
        echo "❌ Critical file missing: models.py"
        exit 1
    fi
    
    # Check static/uploads directory
    if [ -d "static/uploads" ]; then
        upload_count=$(find static/uploads -type f | wc -l)
        echo "📁 Found $upload_count files in static/uploads"
    else
        echo "⚠️  static/uploads directory not found"
    fi
    
    # Check templates directory
    if [ -d "templates" ]; then
        template_count=$(find templates -name "*.html" | wc -l)
        echo "📄 Found $template_count HTML templates"
    else
        echo "⚠️  templates directory not found"
    fi
    
    echo "✅ File integrity verified"
}

# Function to restart the workflow
restart_workflow() {
    echo "🚀 Restarting application workflow..."
    
    # Note: In Replit, workflows are managed by the platform
    # This script prepares the environment for restart
    
    echo "📋 Environment prepared for restart"
    echo "🔄 Please restart the 'Start application' workflow in Replit"
    echo ""
    echo "Steps to complete restart:"
    echo "1. Click the workflow restart button in Replit"
    echo "2. Wait for 'Bot initialized successfully' message"
    echo "3. Verify web interface loads at the provided URL"
    echo "4. Check that all images and assets load correctly"
}

# Function to show environment status
show_status() {
    echo "📊 Environment Status:"
    echo "----------------------------------------"
    
    # Show Git status
    echo "📂 Git Status:"
    git status --short | head -10
    
    echo ""
    echo "🐍 Python Files:"
    find . -name "*.py" -type f | wc -l
    
    echo ""
    echo "📁 Static Files:"
    if [ -d "static" ]; then
        find static -type f | wc -l
    else
        echo "0 (static directory not found)"
    fi
    
    echo ""
    echo "📄 Templates:"
    if [ -d "templates" ]; then
        find templates -name "*.html" | wc -l
    else
        echo "0 (templates directory not found)"
    fi
    
    echo "----------------------------------------"
}

# Main function
main() {
    case "${1:-full}" in
        "stop")
            stop_processes
            ;;
        "clear")
            clear_cache
            ;;
        "verify")
            verify_files
            ;;
        "status")
            show_status
            ;;
        "full")
            stop_processes
            clear_cache
            verify_files
            restart_workflow
            show_status
            ;;
        *)
            echo "Usage: $0 [stop|clear|verify|status|full]"
            echo ""
            echo "Commands:"
            echo "  stop     - Stop running processes"
            echo "  clear    - Clear Python cache"
            echo "  verify   - Verify file integrity"
            echo "  status   - Show environment status"
            echo "  full     - Complete restart workflow (default)"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"