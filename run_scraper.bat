@echo off
echo Running CBCG.me scraper...
cd %~dp0
cd C:\Users\Korisnik\Desktop\CBCG_Chatbot
.venv\Scripts\activate
python apps\functions\local_scraper.py
pause

