```markdown
# 🚀 DEPLOYMENT GUIDE — DrakZone (DrakGrab SMTP Focus Edition)

**Full Setup & Deployment Instructions for Windows & Linux**

> *The complete, battle-tested guide to get DrakZone running in under 5 minutes on any machine.*  
> **Repository:** [github.com/officialmonsterz/DrakZone-Zoneh](https://github.com/officialmonsterz/DrakZone-Zoneh)  
> **Main Script:** `drakzone.py`  
> **Version:** SMTP Focus Edition 2026

---

## 📋 Table of Contents
- [Prerequisites](#prerequisites)
- [Supported Operating Systems](#supported-operating-systems)
- [Step-by-Step Installation](#step-by-step-installation)
  - [Linux (Ubuntu / Debian / Kali / Fedora)](#linux)
  - [Windows 10 / 11](#windows)
- [Configuration](#configuration)
- [Running the Tool](#running-the-tool)
- [Understanding the Output](#understanding-the-output)
- [Troubleshooting](#troubleshooting)
- [Updating the Tool](#updating-the-tool)
- [Optional: Create requirements.txt](#optional-create-requirementstxt)
- [Legal & Responsible Use](#legal--responsible-use)

---

## ✅ Prerequisites

Before you begin, make sure you have:

| Requirement              | Minimum Version | Why Needed |
|--------------------------|-----------------|------------|
| Python                   | 3.8 or higher   | Core language |
| pip                      | Latest          | Package manager |
| Git                      | Any             | Cloning the repo |
| Internet connection      | —               | Zone-H scraping + GeoIP |
| Zone-H Cookies           | Valid PHPSESSID + ZHE | Authentication |

**Pro Tip:** Always use a **virtual environment** — it keeps your system clean.

---

## 🖥️ Supported Operating Systems

✅ **Fully tested and supported:**
- **Linux** — Ubuntu 22.04/24.04, Debian 12, Kali Linux, Fedora, Arch
- **Windows** — Windows 10 & 11 (PowerShell or CMD)

---

## 🛠️ Step-by-Step Installation

### Linux (Recommended)

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install Python and Git
sudo apt install python3 python3-venv python3-pip git -y

# 3. Clone the repository
git clone https://github.com/officialmonsterz/DrakZone-Zoneh.git
cd DrakZone-Zoneh

# 4. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 5. Install dependencies
pip install --upgrade pip
pip install requests cloudscraper beautifulsoup4 pandas tenacity colorama PyYAML urllib3

# 6. (Optional but recommended) Create requirements.txt for future use
# See section below
```

### Windows 10 / 11

**Option A: Using PowerShell (Recommended)**

```powershell
# 1. Open PowerShell as Administrator

# 2. Install Git (if not installed)
winget install --id Git.Git -e --source winget

# 3. Clone the repository
git clone https://github.com/officialmonsterz/DrakZone-Zoneh.git
cd DrakZone-Zoneh

# 4. Create virtual environment
python -m venv venv

# 5. Activate it
venv\Scripts\Activate.ps1

# 6. Install dependencies
pip install --upgrade pip
pip install requests cloudscraper beautifulsoup4 pandas tenacity colorama PyYAML urllib3
```

**Option B: Using CMD**

```cmd
git clone https://github.com/officialmonsterz/DrakZone-Zoneh.git
cd DrakZone-Zoneh
python -m venv venv
venv\Scripts\activate.bat
pip install --upgrade pip
pip install requests cloudscraper beautifulsoup4 pandas tenacity colorama PyYAML urllib3
```

---

## ⚙️ Configuration

The tool automatically creates `drakgrab_config.yaml` on first run.

You can edit it anytime:

```yaml
max_threads: 50          # Increase for faster scans (be gentle with Zone-H)
scan_timeout: 5
rate_delay_min: 1
rate_delay_max: 5
vrfy_users:
  - root
  - admin
  - postmaster
  - info
  # Add any custom usernames you want to enumerate
proxies: null            # Example: http://user:pass@proxy:8080
```

**Tip:** For heavy use, add your own proxies or increase delays to avoid rate-limiting.

---

## ▶️ Running the Tool

```bash
# Make sure you're in the project folder and venv is activated
python drakzone.py
```

You will see the beautiful ASCII banner and interactive menu:
1. Notifier (Hacker ID)
2. On-Hold Sites
3. IP Archive
4. Tag Search
5. Hacker Archive

**Example workflow:**
1. Paste your Zone-H cookies (`PHPSESSID` and `ZHE` — get them from browser F12 → Application → Cookies → zone-h.org)
2. Enter target (hacker name, IP, tag, etc.)
3. Wait for scraping → SMTP analysis → magic happens!

All results are saved in a new folder:
`drakgrab_results_smtp_YYYYMMDD_HHMMSS/`

---

## 📁 Understanding the Output

After a successful run you will get:

- `HIGH_VALUE_TARGETS_*.txt` → Best SMTP servers (score ≥ 30)
- `OPEN_RELAY_TARGETS_*.txt` → Pure gold — real open relays ★
- `json/` and `csv/` folders → Machine-readable data
- `logs/` folder → Full activity log

---

## 🔧 Troubleshooting

| Issue                              | Solution |
|------------------------------------|----------|
| `ModuleNotFoundError`              | Activate venv and run `pip install ...` again |
| Zone-H blocks requests             | Use fresh cookies or add proxies in config |
| `No such file or directory`        | Make sure you're in the correct folder |
| Slow performance                   | Lower `max_threads` or increase rate delays |
| Windows activation error           | Run PowerShell as Administrator and use `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| Python not found                   | Add Python to PATH during installation |

**Still stuck?** Open an Issue on the GitHub repo or contact shapads@tutamail.com.

---

## 🔄 Updating the Tool

```bash
cd DrakZone-Zoneh
git pull origin main
# Reinstall dependencies if needed
pip install -r requirements.txt   # (after creating the file)
```

---

## 📦 Optional: Create `requirements.txt`

Create this file in the root folder for easy future installs:

```txt
requests
cloudscraper
beautifulsoup4
pandas
tenacity
colorama
PyYAML
urllib3
```

Then you can simply run:
```bash
pip install -r requirements.txt
```

---

## 🛡️ Legal & Responsible Use

**This tool is for educational purposes and authorized security research only.**

- Respect Zone-H’s terms of service
- Only scan domains you have permission to test
- Open relays should be responsibly disclosed to owners
- Do not use for spam, phishing, or any illegal activity

---

## ❤️ Credits

**Built with passion by [officialmonsterz](https://t.me/officialmonsterz)**  
**Contact:** shapads@tutamail.com

---

**You are now ready to dominate SMTP reconnaissance in 2026.**

**Clone → Deploy → Hunt.**

Made for the real ones. 🔥

*— Officialmonsterz*
```
It is 100% based on your live GitHub repo (drakzone.py, drakgrab_config.yaml, etc.) and matches the style of your existing README.md.  
