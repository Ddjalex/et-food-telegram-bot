# Quick Git Commands for ET-FOOD

## 🚀 Most Common Commands

### Commit & Push Changes
```bash
./git_workflow.sh full
```

### Pull Updates & Restart
```bash
./git_workflow.sh pull
./restart_after_pull.sh full
# Then restart "Start application" workflow in Replit
```

### Check File Status
```bash
./git_workflow.sh verify
```

### Emergency Reset (if files are missing)
```bash
git fetch origin main
git reset --hard origin/main
./restart_after_pull.sh full
```

## 📁 File Tracking Status

- ✅ **74+ food images** in static/uploads/
- ✅ **40+ Python files** (.py)
- ✅ **HTML templates** and CSS
- ✅ **Configuration files**
- ❌ **Cache files** (auto-excluded)
- ❌ **Database files** (auto-excluded)

## 🔧 Setup (One Time)
```bash
chmod +x *.sh
./git_hooks_setup.sh
```

## 📊 Status Check
```bash
./restart_after_pull.sh status
```