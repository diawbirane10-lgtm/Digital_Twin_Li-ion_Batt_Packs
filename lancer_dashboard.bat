@echo off
title Battery Digital Twin — Dashboard
cd /d "%~dp0"
echo Demarrage du dashboard...
call conda activate base 2>nul || echo (conda non disponible, utilisation Python systeme)
python -m streamlit run visualization/dashboard/app.py --server.port 8501 --browser.gatherUsageStats false
pause
