                             ULTIMATE ZONE-H DEFACEMENT HUNTER
                    =================================================
                    Author: willsmith32701@gmail.com
                    Production-Ready Pentest Recon Tool

🎯 WHAT IT DOES:
- Scrapes Zone-H defacement archives (5 modes)
- Nmap service scanning (top 50 ports)
- Nuclei vulnerability detection
- Shodan intelligence lookup
- GeoIP/ASn mapping
- AI-powered vuln analysis
- Auto-scores targets (0-50+)

⚡ SPEED:
- 100 domains: 15-20 mins
- 1000 domains: 2-3 hours
- 50 parallel threads

📊 OUTPUTS:
⭐ HIGH_VALUE_TARGETS_*.txt (MUST WATCH)
📊 drakgrab_results_*.json
📊 drakgrab_results_*.csv
📁 Raw scraped domains

🚀 INSTALL:
pip install -r requirements.txt
sudo apt install nmap nuclei

🎮 USAGE:
python3 drakgrab.py

⭐ HIGH VALUE = Score 10+ (cPanel/RDP/Exploitable)

1️⃣ SETUP:
$ pip install requests beautifulsoup4 pyyaml pandas cloudscraper tenacity colorama
$ sudo apt install nmap nuclei  # Kali/Debian

2️⃣ GET COOKIES:
• Open zone-h.org
• F12 → Application → Storage → Cookies
• Copy PHPSESSID & ZHE values

3️⃣ RUN:
$ python3 drakgrab.py

4️⃣ MENU:
1. Notifier    → hacker123
2. On-Hold     → (no input)
3. IP Archive  → 1.2.3.4
4. Tag         → sql
5. Hacker      → moroccan

5️⃣ WATCH:
Page 1: +25 domains (Total: 45)
[  1/245] target.com     | Score:25 | Ports:5  ← GREEN = $$$$

6️⃣ RESULTS:
⭐ HIGH_VALUE_TARGETS_20241213_143022.txt  ← YOUR GOLD
   DOMAIN: target.com
   SCORE: 25
   IP: 1.2.3.4
   PORTS: 22,80,443,2083,3389
   SERVICES: 2083:cPanel,3389:RDP

PRO TIPS:
• Score 20+ = RDP+cPanel = OWNED
• Run multiple notifiers daily
• Import CSV to Burp/Masscan
• Config: drakgrab_config.yaml

willsmith32701@gmail.com
