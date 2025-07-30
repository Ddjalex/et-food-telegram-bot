#!/bin/bash
# Set up Git hooks for automated workflow

echo "🔧 Setting up Git hooks for ET-FOOD project..."

# Create hooks directory if it doesn't exist
mkdir -p .git/hooks

# Pre-commit hook - ensures files are properly formatted before commit
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Pre-commit hook for ET-FOOD project

echo "🔍 Running pre-commit checks..."

# Check for Python syntax errors
echo "🐍 Checking Python syntax..."
python_errors=0
for file in $(git diff --cached --name-only --diff-filter=ACM | grep '\.py$'); do
    if [ -f "$file" ]; then
        python -m py_compile "$file" 2>/dev/null || {
            echo "❌ Syntax error in $file"
            python_errors=$((python_errors + 1))
        }
    fi
done

if [ $python_errors -gt 0 ]; then
    echo "❌ Found $python_errors Python syntax errors. Commit aborted."
    exit 1
fi

# Check for large files
echo "📏 Checking file sizes..."
large_files=0
for file in $(git diff --cached --name-only --diff-filter=ACM); do
    if [ -f "$file" ]; then
        size=$(wc -c < "$file")
        if [ $size -gt 10485760 ]; then  # 10MB
            echo "⚠️  Large file detected: $file ($(($size / 1024 / 1024))MB)"
            large_files=$((large_files + 1))
        fi
    fi
done

if [ $large_files -gt 0 ]; then
    echo "⚠️  Found $large_files large files. Consider if they should be committed."
    echo "Continue anyway? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Commit aborted."
        exit 1
    fi
fi

echo "✅ Pre-commit checks passed"
EOF

# Post-commit hook - shows what was committed
cat > .git/hooks/post-commit << 'EOF'
#!/bin/bash
# Post-commit hook for ET-FOOD project

echo "✅ Commit completed successfully!"
echo "📝 Latest commit:"
git log --oneline -1

# Show summary of changes
echo "📊 Commit summary:"
git diff --stat HEAD~1 HEAD

echo ""
echo "💡 Next steps:"
echo "  - Push to GitHub: git push origin main"
echo "  - Or use: ./git_workflow.sh push"
EOF

# Make hooks executable
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/post-commit

echo "✅ Git hooks installed successfully!"
echo ""
echo "Hooks installed:"
echo "  📋 pre-commit  - Checks Python syntax and file sizes"
echo "  📝 post-commit - Shows commit summary"