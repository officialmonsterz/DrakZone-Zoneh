#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║  ███╗   ███╗███████╗███╗   ███╗ ██████╗     ██████╗  ██████╗ ██╗  ██╗               ║
║  ████╗ ████║██╔════╝████╗ ████║██╔════╝     ██╔══██╗██╔═══██╗██║ ██╔╝               ║
║  ██╔████╔██║█████╗  ██╔████╔██║██║             ██████╔╝██║   ██║█████╔╝                ║
║  ██║╚██╔╝██║██╔══╝  ██║╚██╔╝██║██║             ██╔══██╗██║   ██║██╔═██╗                ║
║  ██║ ╚═╝ ██║███████╗██║ ╚═╝ ██║╚██████╗    ██║  ██║╚██████╔╝██║  ██║                ║
║  ╚═╝     ╚═╝╚══════╝╚═╝     ╚═╝ ╚═════╝    ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝                ║
║                                                                                      ║
║  SMTP FOCUS EDITION 2026  |  Zone-H Scraper + SMTP Relay Hunter                      ║
║  Credits: github.com/officialmonsterz  |  t.me/officialmonsterz                       ║
║  Multi-Threaded • SMTP Banner Grab • Open Relay Test • VRFY Enum • Scoring           ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

import requests
import re
import os
import sys
import socket
import time
import random
import json
import csv
import logging
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from colorama import Fore, Style, init
import pandas as pd
import tenacity
from bs4 import BeautifulSoup
import cloudscraper

# Initialize colorama
init(autoreset=True)

# Color shortcuts
fr = Fore.RED
fc = Fore.CYAN
fw = Fore.WHITE
fy = Fore.YELLOW
fg = Fore.GREEN
fm = Fore.MAGENTA
sd = Style.DIM
sn = Style.NORMAL
sb = Style.BRIGHT

# ── SMTP Constants ──────────────────────────────────────────────────────────────────
SMTP_PORTS = [25, 465, 587, 2525]
CPANEL_PORTS = [2082, 2083, 2086, 2087]

# Scoring weights — SMTP-centric
SCORE_SMTP_25_OPEN = 30       # Port 25 open = primary target
SCORE_SMTP_465_OPEN = 25      # SMTPS
SCORE_SMTP_587_OPEN = 20      # Submission port
SCORE_SMTP_2525_OPEN = 15     # Alternate SMTP
SCORE_OPEN_RELAY = 100        # GOLD — open relay found
SCORE_USER_ENUM = 40          # VRFY/EXPN enabled
SCORE_STARTTLS = 10           # STARTTLS advertised
SCORE_BANNER_SOFTWARE = 10    # Software identified from banner
SCORE_CPANEL_PORT = 25        # cPanel port open (secondary priority)

# Default VRFY user list
DEFAULT_VRFY_USERS = [
    "root", "admin", "info", "support", "contact", "postmaster",
    "noreply", "mail", "sales", "test", "user", "webmaster",
    "abuse", "hostmaster", "admin@", "administrator"
]

# Modern 2026 User Agents
USER_AGENTS_2026 = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0"
]


class ZoneHScraperSMTP:
    """Zone-H Scraper + SMTP Vulnerability Analyzer — SMTP Focus Edition"""

    def __init__(self, config_path="drakgrab_config.yaml"):
        self.results_folder = "drakgrab_results"
        self.config_path = config_path
        self.config = self.load_config()
        self.session = None
        self.scraper = None
        self.setup_logging()
        self.create_results_folder()

    def load_config(self):
        default_config = {
            'proxies': None,
            'max_threads': 50,
            'scan_timeout': 5,
            'retry_attempts': 3,
            'rate_delay_min': 1,
            'rate_delay_max': 5,
            'smtp_ports': SMTP_PORTS,
            'cpanel_ports': CPANEL_PORTS,
            'vrfy_users': DEFAULT_VRFY_USERS,
            'verify_ssl': True
        }

        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                cfg = yaml.safe_load(f)
                if cfg:
                    default_config.update(cfg)

        with open(self.config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)

        return default_config

    def setup_logging(self):
        log_dir = f"{self.results_folder}/logs"
        os.makedirs(log_dir, exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f"{log_dir}/drakgrab_smtp.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def create_results_folder(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results_folder = f"{self.results_folder}_smtp_{timestamp}"
        os.makedirs(self.results_folder, exist_ok=True)
        os.makedirs(f"{self.results_folder}/json", exist_ok=True)
        os.makedirs(f"{self.results_folder}/csv", exist_ok=True)
        os.makedirs(f"{self.results_folder}/logs", exist_ok=True)

    def init_session(self):
        if self.session is None:
            self.session = requests.Session()
            retry_strategy = Retry(
                total=self.config['retry_attempts'],
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504]
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)

        if self.scraper is None:
            self.scraper = cloudscraper.create_scraper()

    # ═══════════════════════════════════════════════════════════════════════════════
    #  ZONE-H SCRAPING (Unchanged core — compulsory)
    # ═══════════════════════════════════════════════════════════════════════════════

    @tenacity.retry(stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_exponential(multiplier=1, min=4, max=10))
    def get_page(self, url, cookies=None):
        self.init_session()
        headers = {
            "User-Agent": random.choice(USER_AGENTS_2026),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

        time.sleep(random.uniform(self.config['rate_delay_min'], self.config['rate_delay_max']))

        response = self.scraper.get(url, cookies=cookies, headers=headers, timeout=20, proxies=self.config['proxies'])
        response.raise_for_status()
        return response

    def parse_pagination(self, content):
        patterns = [
            r'Page\s+\d+\s+of\s+(\d+)',
            r'page=(\d+)[^>]*>Next',
            r'(\d+)\s+pages?',
            r'page\s+\d+\s+sur\s+(\d+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return min(int(match.group(1)), 100)
        return 50

    def extract_domains_bs4(self, content):
        soup = BeautifulSoup(content, 'html.parser')
        domains = set()

        selectors = [
            'td a[href*="/mirror/"]',
            'td a[href*="zone-h"]',
            'table td a',
            'tr td:nth-of-type(2)',
            '.defaced-url',
            'td'
        ]

        for selector in selectors:
            for elem in soup.select(selector):
                text = elem.get_text(strip=True)
                if text and re.search(r'\.[a-z]{2,}', text):
                    domain = self.clean_domain(text)
                    if domain:
                        domains.add(domain)
        return list(domains)

    def clean_domain(self, text):
        text = re.sub(r'[^\w\.\-/]', ' ', text)
        text = re.sub(r'https?://?', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        parts = text.split('/')
        for part in parts:
            match = re.match(r'([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,})', part)
            if match:
                return f"http://{match.group(1)}"
        return None

    def scrape_archive(self, base_url, output_file, cookies, mode='notifier'):
        self.logger.info(f"DrakGrab: Starting {mode} scrape")
        all_domains = set()

        try:
            response = self.get_page(base_url, cookies)
            total_pages = self.parse_pagination(response.text)

            print(fg + f"📄 Found {total_pages} pages to scrape...")

            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = []
                for page in range(1, total_pages + 1):
                    page_url = f"{base_url.replace('/page=', '/')}/page={page}" if '/page=' not in base_url else f"{base_url}&page={page}"
                    future = executor.submit(self.get_page, page_url, cookies)
                    futures.append((page, future))

                for page_num, future in futures:
                    try:
                        response = future.result(timeout=45)
                        domains = self.extract_domains_bs4(response.text)
                        all_domains.update(domains)
                        print(fg + f"📋 Page {page_num}: +{len(domains)} (Total: {len(all_domains)})")
                    except Exception as e:
                        self.logger.error(f"Page {page_num}: {e}")

            with open(f"{self.results_folder}/{output_file}", 'w', encoding='utf-8') as f:
                for domain in sorted(all_domains):
                    f.write(domain + '\n')

            print(fg + f"💾 Saved {len(all_domains)} domains to {output_file}")
            return list(all_domains)

        except Exception as e:
            self.logger.error(f"Scrape failed: {e}")
            return []

    # ═══════════════════════════════════════════════════════════════════════════════
    #  SMTP ANALYSIS CORE  (All new — your priority features)
    # ═══════════════════════════════════════════════════════════════════════════════

    def smtp_scan_ports(self, ip):
        """
        COMPULSORY: Scan only SMTP ports (25, 465, 587, 2525) + cPanel ports.
        Fast socket connect, no heavy nmap.
        """
        open_ports = {}
        all_ports = self.config['smtp_ports'] + self.config['cpanel_ports']

        for port in all_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.config['scan_timeout'])
                result = sock.connect_ex((ip, port))
                if result == 0:
                    open_ports[port] = "open"
                sock.close()
            except:
                pass

        return open_ports

    def smtp_banner_grab(self, ip, port):
        """
        VERY IMPORTANT: Grab SMTP banner to identify software + version.
        Returns banner string or empty string.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.config['scan_timeout'])
            sock.connect((ip, port))
            banner = sock.recv(1024).decode('utf-8', errors='ignore').strip()
            sock.close()
            return banner
        except:
            return ""

    def smtp_get_ehlo_response(self, ip, port):
        """
        Get EHLO response to identify supported features (STARTTLS, AUTH methods).
        Returns the full EHLO response string.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.config['scan_timeout'])
            sock.connect((ip, port))
            sock.recv(1024)  # banner
            sock.send(b"EHLO drakgrab-scan.local\r\n")
            time.sleep(0.5)
            ehlo_resp = sock.recv(4096).decode('utf-8', errors='ignore')
            sock.close()
            return ehlo_resp
        except:
            return ""

    def check_starttls(self, ehlo_response):
        """
        IMPORTANT: Check if STARTTLS is advertised in EHLO response.
        """
        if "STARTTLS" in ehlo_response.upper():
            return True
        return False

    def detect_auth_mechanisms(self, ehlo_response):
        """
        IMPORTANT: Detect AUTH mechanisms from EHLO response.
        Returns list of auth methods (LOGIN, PLAIN, CRAM-MD5, etc.)
        """
        auth_methods = []
        for line in ehlo_response.split('\n'):
            line = line.strip().upper()
            if line.startswith("250 AUTH") or "AUTH=" in line:
                # Extract mechanisms
                if "AUTH=" in line:
                    mechanisms = line.split("AUTH=")[1].strip()
                    auth_methods = [m.strip() for m in mechanisms.split() if m.strip()]
                else:
                    mechanisms = line.replace("250 AUTH", "").strip()
                    auth_methods = [m.strip() for m in mechanisms.split() if m.strip()]
        return auth_methods

    def check_open_relay(self, ip, port=25):
        """
        COMPULSORY: Test if SMTP server allows open relay.
        Tests multiple external domains to avoid whitelist bypass.
        """
        test_domains = [
            "external-test@gmail.com",
            "testuser@yahoo.com",
            "verify@hotmail.com",
            "nobody@outlook.com",
            "random@protonmail.com"
        ]

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(15)
            sock.connect((ip, port))
            sock.recv(1024)

            sock.send(b"EHLO drakgrab-test.local\r\n")
            time.sleep(0.3)
            sock.recv(1024)

            sock.send(b"MAIL FROM:<verify@gmail.com>\r\n")
            time.sleep(0.3)
            sock.recv(1024)

            for rcpt_to in test_domains:
                sock.send(f"RCPT TO:<{rcpt_to}>\r\n".encode())
                time.sleep(0.2)
                response = sock.recv(1024).decode('utf-8', errors='ignore')

                if "250" in response:
                    sock.send(b"QUIT\r\n")
                    sock.close()
                    return True, rcpt_to

            sock.send(b"QUIT\r\n")
            sock.close()
            return False, None
        except:
            return False, None

    def smtp_vrfy_enum(self, ip, port=25):
        """
        IMPORTANT: Attempt VRFY/EXPN to enumerate valid users.
        Returns list of valid usernames found.
        """
        valid_users = []
        users = self.config.get('vrfy_users', DEFAULT_VRFY_USERS)

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(15)
            sock.connect((ip, port))
            sock.recv(1024)  # banner

            sock.send(b"EHLO drakgrab-enum.local\r\n")
            time.sleep(0.3)
            sock.recv(1024)

            for user in users:
                try:
                    sock.send(f"VRFY {user}\r\n".encode())
                    time.sleep(0.1)
                    resp = sock.recv(1024).decode('utf-8', errors='ignore')
                    # 250 = user exists, 252 = cannot VRFY but will try delivery
                    # 550/551 = no such user
                    if "250" in resp or "252" in resp:
                        valid_users.append(user)
                except:
                    continue

            sock.send(b"QUIT\r\n")
            sock.close()
        except:
            pass

        return valid_users

    def identify_smtp_software(self, banner):
        """
        Attempt to identify SMTP server software from banner string.
        Returns (software_name, version_or_None)
        """
        banner_upper = banner.upper()

        patterns = [
            (r'EXIM\s+(\d+\.\d+)', 'Exim'),
            (r'POSTFIX\s+(\S+)', 'Postfix'),
            (r'SENDMAIL\s+(\S+)', 'Sendmail'),
            (r'MICROSOFT\s+ESMTP\s+MAIL\s+SERVICE', 'Exchange/IIS'),
            (r'COURIER-MTA', 'Courier'),
            (r'QMAIL', 'qmail'),
            (r'OPENSMTPD', 'OpenSMTPD'),
            (r'DOVEATT', 'Dovecot'),
        ]

        for pattern, name in patterns:
            match = re.search(pattern, banner_upper)
            if match:
                version = match.group(1) if match.lastindex and match.group(1) else None
                return name, version

        # Fallback: try to extract any identifiable name
        known_servers = ['EXIM', 'POSTFIX', 'SENDMAIL', 'QMAIL', 'COURIER', 'DOVECOT']
        for srv in known_servers:
            if srv in banner_upper:
                return srv.capitalize(), None

        return "Unknown", None

    # ═══════════════════════════════════════════════════════════════════════════════
    #  SCORING ENGINE  (SMTP-focused rewrite)
    # ═══════════════════════════════════════════════════════════════════════════════

    def calculate_score(self, smtp_data):
        """
        COMPULSORY: Calculate priority score based on SMTP findings.
        SMTP port 25 -> highest weight. Open relay -> critical.
        cPanel ports secondary.
        """
        score = 0
        reasons = []

        open_ports = smtp_data.get('open_ports', {})

        # SMTP port scoring
        if 25 in open_ports:
            score += SCORE_SMTP_25_OPEN
            reasons.append(f"Port 25 open (+{SCORE_SMTP_25_OPEN})")
        if 465 in open_ports:
            score += SCORE_SMTP_465_OPEN
            reasons.append(f"Port 465 open (+{SCORE_SMTP_465_OPEN})")
        if 587 in open_ports:
            score += SCORE_SMTP_587_OPEN
            reasons.append(f"Port 587 open (+{SCORE_SMTP_587_OPEN})")
        if 2525 in open_ports:
            score += SCORE_SMTP_2525_OPEN
            reasons.append(f"Port 2525 open (+{SCORE_SMTP_2525_OPEN})")

        # Open relay — gold
        if smtp_data.get('open_relay', False):
            score += SCORE_OPEN_RELAY
            reasons.append(f"OPEN RELAY DETECTED (+{SCORE_OPEN_RELAY}) ★")

        # User enumeration
        vrfy_count = len(smtp_data.get('valid_users', []))
        if vrfy_count > 0:
            score += SCORE_USER_ENUM
            reasons.append(f"VRFY/EXPN enabled ({vrfy_count} users) (+{SCORE_USER_ENUM})")

        # STARTTLS
        if smtp_data.get('starttls', False):
            score += SCORE_STARTTLS
            reasons.append(f"STARTTLS supported (+{SCORE_STARTTLS})")

        # Banner software identified
        if smtp_data.get('smtp_software') and smtp_data['smtp_software'] != "Unknown":
            score += SCORE_BANNER_SOFTWARE
            reasons.append(f"Software: {smtp_data['smtp_software']} (+{SCORE_BANNER_SOFTWARE})")

        # cPanel ports (secondary)
        for port in self.config['cpanel_ports']:
            if port in open_ports:
                score += SCORE_CPANEL_PORT
                reasons.append(f"cPanel port {port} open (+{SCORE_CPANEL_PORT})")

        return score, reasons

    # ═══════════════════════════════════════════════════════════════════════════════
    #  SINGLE DOMAIN ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════════

    def analyze_domain_smtp(self, domain):
        """
        Full SMTP-focused analysis pipeline for a single domain.
        """
        result = {
            'domain': domain,
            'score': 0,
            'score_reasons': [],
            'ip': '',
            'open_ports': {},
            'smtp_banners': {},
            'ehlo_responses': {},
            'starttls': False,
            'auth_mechanisms': [],
            'open_relay': False,
            'open_relay_port': None,
            'valid_users': [],
            'smtp_software': '',
            'smtp_version': '',
            'geo': {},
            'status': 'pending'
        }

        try:
            # Extract clean hostname
            hostname = domain.replace('http://', '').replace('https://', '').strip('/')

            # DNS resolution
            try:
                ip = socket.gethostbyname(hostname)
                result['ip'] = ip
            except socket.gaierror:
                result['status'] = 'no-dns'
                return result

            # ── Port scan (SMTP only + cPanel) ──
            open_ports = self.smtp_scan_ports(ip)
            result['open_ports'] = open_ports

            # If no SMTP ports are open, mark and return early
            smtp_found = any(p in open_ports for p in self.config['smtp_ports'])
            if not smtp_found:
                result['status'] = 'no-smtp'
                return result

            # ── Banner grabbing on each open SMTP port ──
            banners = {}
            ehlo_responses = {}
            for port in self.config['smtp_ports']:
                if port in open_ports:
                    banner = self.smtp_banner_grab(ip, port)
                    if banner:
                        banners[port] = banner
                    ehlo = self.smtp_get_ehlo_response(ip, port)
                    if ehlo:
                        ehlo_responses[port] = ehlo

            result['smtp_banners'] = banners
            result['ehlo_responses'] = ehlo_responses

            # ── Identify software from primary port 25 (or first available) ──
            primary_port = 25 if 25 in banners else (list(banners.keys())[0] if banners else None)
            if primary_port:
                software, version = self.identify_smtp_software(banners[primary_port])
                result['smtp_software'] = software
                result['smtp_version'] = version

            # ── STARTTLS detection (check all open SMTP ports) ──
            for port in self.config['smtp_ports']:
                if port in ehlo_responses:
                    if self.check_starttls(ehlo_responses[port]):
                        result['starttls'] = True
                        break

            # ── Auth mechanisms ──
            all_auth = []
            for port in self.config['smtp_ports']:
                if port in ehlo_responses:
                    auth = self.detect_auth_mechanisms(ehlo_responses[port])
                    all_auth.extend(auth)
            result['auth_mechanisms'] = list(set(all_auth))

            # ── Open relay test (port 25 first, fallback to other SMTP ports) ──
            relay_ports_to_test = [25, 587, 465, 2525]
            for rp in relay_ports_to_test:
                if rp in open_ports:
                    is_relay, relay_domain = self.check_open_relay(ip, port=rp)
                    if is_relay:
                        result['open_relay'] = True
                        result['open_relay_port'] = rp
                        result['relay_rcpt_domain'] = relay_domain
                        break

            # ── VRFY user enumeration (port 25, fallback) ──
            enum_port = 25 if 25 in open_ports else (587 if 587 in open_ports else None)
            if enum_port:
                valid = self.smtp_vrfy_enum(ip, port=enum_port)
                result['valid_users'] = valid

            # ── GeoIP lookup ──
            try:
                resp = requests.get(
                    f"http://ip-api.com/json/{ip}?fields=status,message,country,city,org,asn,isp",
                    timeout=8
                )
                geo_data = resp.json()
                if geo_data.get('status') == 'success':
                    result['geo'] = geo_data
            except:
                pass

            # ── Calculate score ──
            score, reasons = self.calculate_score(result)
            result['score'] = score
            result['score_reasons'] = reasons
            result['status'] = 'ok'

        except Exception as e:
            self.logger.error(f"Error analyzing {domain}: {e}")
            result['status'] = 'error'

        return result

    # ═══════════════════════════════════════════════════════════════════════════════
    #  BULK ANALYSIS + EXPORT
    # ═══════════════════════════════════════════════════════════════════════════════

    def enhanced_analysis_bulk(self, domains_file):
        """Run SMTP analysis on all domains from scraped file."""
        print(fy + "🔥 DRAKGRAB SMTP ANALYSIS STARTING...")

        with open(domains_file, 'r') as f:
            domains = [line.strip().replace('http://', '').rstrip('/') for line in f if line.strip()]

        domains = list(set(domains))
        print(fg + f"🎯 Analyzing {len(domains)} unique domains for SMTP...")

        results = []
        with ThreadPoolExecutor(max_workers=self.config['max_threads']) as executor:
            future_to_domain = {executor.submit(self.analyze_domain_smtp, d): d for d in domains}

            for i, future in enumerate(as_completed(future_to_domain), 1):
                domain = future_to_domain[future]
                try:
                    result = future.result(timeout=300)
                    results.append(result)

                    score = result.get('score', 0)
                    ip = result.get('ip', 'N/A')
                    status = result.get('status', '?')
                    open_relay = "★ RELAY" if result.get('open_relay') else ""
                    ports = list(result.get('open_ports', {}).keys())

                    if open_relay:
                        print(fm + f"[{i:3d}/{len(domains)}] {domain[:35]:35} | Score:{score:3d} | IP:{ip:15} | Ports:{str(ports):20} {sb}{fr}{open_relay}")
                    elif score >= 30:
                        print(fg + f"[{i:3d}/{len(domains)}] {domain[:35]:35} | Score:{score:3d} | IP:{ip:15} | Ports:{str(ports):20}")
                    elif status == 'no-smtp':
                        print(fy + f"[{i:3d}/{len(domains)}] {domain[:35]:35} | No SMTP ports")
                    elif status == 'no-dns':
                        print(fr + f"[{i:3d}/{len(domains)}] {domain[:35]:35} | No DNS")
                    else:
                        print(fy + f"[{i:3d}/{len(domains)}] {domain[:35]:35} | Score:{score:3d} | {status}")

                except Exception as e:
                    print(fr + f"[{i:3d}/{len(domains)}] {domain[:35]:35} | TIMEOUT/ERROR")
                    self.logger.error(f"Timeout/error for {domain}: {e}")

        # Sort by score descending
        results.sort(key=lambda x: x['score'], reverse=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # ── JSON Export ──
        json_file = f"{self.results_folder}/json/drakgrab_smtp_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=1, default=str)
        print(fg + f"\n📊 JSON: {json_file}")

        # ── CSV Export ──
        csv_file = f"{self.results_folder}/csv/drakgrab_smtp_{timestamp}.csv"
        # Prepare flattened CSV data
        csv_rows = []
        for r in results:
            csv_rows.append({
                'domain': r.get('domain', ''),
                'score': r.get('score', 0),
                'ip': r.get('ip', ''),
                'status': r.get('status', ''),
                'open_ports': ', '.join(map(str, r.get('open_ports', {}).keys())),
                'smtp_software': r.get('smtp_software', ''),
                'smtp_version': r.get('smtp_version', ''),
                'open_relay': r.get('open_relay', False),
                'open_relay_port': r.get('open_relay_port', ''),
                'starttls': r.get('starttls', False),
                'auth_mechanisms': ', '.join(r.get('auth_mechanisms', [])),
                'valid_users': ', '.join(r.get('valid_users', [])),
                'country': r.get('geo', {}).get('country', ''),
                'city': r.get('geo', {}).get('city', ''),
                'org': r.get('geo', {}).get('org', ''),
                'isp': r.get('geo', {}).get('isp', ''),
                'asn': r.get('geo', {}).get('asn', ''),
                'score_reasons': '; '.join(r.get('score_reasons', []))
            })
        pd.DataFrame(csv_rows).to_csv(csv_file, index=False)
        print(fg + f"📊 CSV:  {csv_file}")

        # ── HIGH VALUE TARGETS (Score 30+ or open relay) ──
        high_value = [r for r in results if r['score'] >= 30 or r.get('open_relay')]
        hv_file = f"{self.results_folder}/HIGH_VALUE_TARGETS_{timestamp}.txt"
        with open(hv_file, 'w', encoding='utf-8') as f:
            f.write("=" * 52 + "\n")
            f.write("DRAKGRAB SMTP HIGH VALUE TARGETS\n")
            f.write("=" * 52 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total targets: {len(high_value)}\n")
            f.write("=" * 70 + "\n\n")

            for r in high_value:
                f.write(f"DOMAIN:      {r['domain']}\n")
                f.write(f"SCORE:       {r['score']}\n")
                f.write(f"IP:          {r.get('ip', 'N/A')}\n")
                f.write(f"STATUS:      {r.get('status', 'N/A')}\n")
                f.write(f"OPEN PORTS:  {', '.join(map(str, r.get('open_ports', {}).keys()))}\n")
                f.write(f"SOFTWARE:    {r.get('smtp_software', 'Unknown')} {r.get('smtp_version', '')}\n")
                f.write(f"OPEN RELAY:  {'YES (port ' + str(r.get('open_relay_port','')) + ')' if r.get('open_relay') else 'No'}\n")
                f.write(f"STARTTLS:    {r.get('starttls', False)}\n")
                f.write(f"AUTH:        {', '.join(r.get('auth_mechanisms', [])) or 'None advertised'}\n")
                f.write(f"VALID USERS: {', '.join(r.get('valid_users', [])) or 'None found'}\n")
                f.write(f"COUNTRY:     {r.get('geo', {}).get('country', 'N/A')}\n")
                f.write(f"ORG:         {r.get('geo', {}).get('org', 'N/A')}\n")
                f.write(f"ISP:         {r.get('geo', {}).get('isp', 'N/A')}\n")
                f.write(f"REASONS:     {'; '.join(r.get('score_reasons', []))}\n")
                f.write("-" * 70 + "\n\n")

        print(fg + f"📄 TXT:  {hv_file}")

        # ── OPEN RELAYS ONLY (separate file — your special request) ──
        open_relays = [r for r in results if r.get('open_relay')]
        relay_file = f"{self.results_folder}/OPEN_RELAY_TARGETS_{timestamp}.txt"
        with open(relay_file, 'w', encoding='utf-8') as f:
            f.write("=" * 50 + "\n")
            f.write("OPEN RELAY SERVERS (SMTP)\n")
            f.write("=" * 50 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total open relays found: {len(open_relays)}\n")
            f.write("=" * 70 + "\n\n")
            for idx, r in enumerate(open_relays, 1):
                f.write(f"{idx:3d}. {r['domain']:35} | IP: {r.get('ip','N/A'):15} | Port: {r.get('open_relay_port','?')} | Score: {r['score']}\n")

        print(fg + f"📄 OPEN RELAYS: {relay_file} ({len(open_relays)} targets)")

        # Summary stats
        smtp_found = len([r for r in results if r['status'] == 'ok'])
        no_smtp = len([r for r in results if r['status'] == 'no-smtp'])
        no_dns = len([r for r in results if r['status'] == 'no-dns'])
        errors = len([r for r in results if r['status'] == 'error'])

        print(fg + f"\n{'=' * 50}")
        print(sb + f"📊 DRAKGRAB SMTP COMPLETE!")
        print(fg + f"   Total domains analyzed: {len(results)}")
        print(fg + f"   SMTP servers found:     {smtp_found}")
        print(fr + f"   Open relays:            {len(open_relays)} ★")
        print(fy + f"   No SMTP ports:          {no_smtp}")
        print(fr + f"   No DNS resolution:      {no_dns}")
        print(fr + f"   Errors:                 {errors}")
        print(fg + f"   High value targets:     {len(high_value)}")
        print(fg + f"{'=' * 50}")
        print(fg + f"📁 All results: {self.results_folder}/")

        return results


def display_banner():
    banner = f"""
{fc}╔══════════════════════════════════════════════════════════════════════════════════════╗
{fc}║                                                                                      ║
{fc}║  {sb}{fy}███╗   ███╗███████╗███╗   ███╗ ██████╗     ██████╗  ██████╗ ██╗  ██╗           {fc}║
{fc}║  {sb}{fy}████╗ ████║██╔════╝████╗ ████║██╔════╝     ██╔══██╗██╔═══██╗██║ ██╔╝           {fc}║
{fc}║  {sb}{fy}██╔████╔██║█████╗  ██╔████╔██║██║             ██████╔╝██║   ██║█████╔╝            {fc}║
{fc}║  {sb}{fy}██║╚██╔╝██║██╔══╝  ██║╚██╔╝██║██║             ██╔══██╗██║   ██║██╔═██╗            {fc}║
{fc}║  {sb}{fy}██║ ╚═╝ ██║███████╗██║ ╚═╝ ██║╚██████╗    ██║  ██║╚██████╔╝██║  ██║            {fc}║
{fc}║  {sb}{fy}╚═╝     ╚═╝╚══════╝╚═╝     ╚═╝ ╚═════╝    ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝            {fc}║
{fc}║                                                                                      ║
{fc}║  {fg}SMTP FOCUS EDITION 2026  |  Zone-H Scraper + SMTP Relay Hunter                     {fc}║
{fc}║  {fg}Credits: github.com/officialmonsterz | shapads@tutamail.com                        {fc}║
{fc}║  {fg}SMTP Scan • Banner Grab • Open Relay • VRFY Enum • STARTTLS • Scoring             {fc}║
{fc}╚══════════════════════════════════════════════════════════════════════════════════════╝
{sn}
    """
    print(banner)


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def main():
    clear_screen()
    display_banner()

    scraper = ZoneHScraperSMTP()

    print(fc + "\n🎯 DRAKGRAB Zone-H Archive Options:")
    print(fc + "  1. Notifier (Hacker ID)")
    print(fc + "  2. On-Hold Sites")
    print(fc + "  3. IP Archive")
    print(fc + "  4. Tag Search")
    print(fc + "  5. Hacker Archive")

    choice = input(fy + "\nSelect (1-5): ").strip()

    print(fy + "\n🔑 Zone-H Cookies (F12 → Application → Cookies):")
    cookies = {
        "PHPSESSID": input(fy + "PHPSESSID: ").strip(),
        "ZHE": input(fy + "ZHE: ").strip()
    }

    target = ""
    if choice in ['1', '4', '5']:
        target = input(fy + "Enter Notifier/Hacker/Tag: ").strip()
    elif choice == '3':
        target = input(fy + "Enter IP: ").strip()

    # Build URL (kept as HTTP since Zone-H still uses it)
    if choice == '1':
        url = f"http://www.zone-h.org/archive/notifier={target}"
        output = f"notifier_{target}.txt"
    elif choice == '2':
        url = "http://zone-h.org/archive/published=0"
        output = "onhold.txt"
    elif choice == '3':
        url = f"http://www.zone-h.org/archive/ip={target}"
        output = f"ip_{target}.txt"
    elif choice == '4':
        url = f"http://www.zone-h.org/archive/tag={target}"
        output = f"tag_{target}.txt"
    elif choice == '5':
        url = f"http://www.zone-h.org/archive/hacker={target}"
        output = f"hacker_{target}.txt"
    else:
        print(fr + "❌ Invalid choice!")
        return

    print(fg + f"\n🚀 Starting DRAKGRAB SMTP Edition: {url}")
    print(fg + f"📁 Results → {scraper.results_folder}")

    domains = scraper.scrape_archive(url, output, cookies, f"mode_{choice}")

    if domains:
        print(fg + f"\n✅ Scraped {len(domains)} domains!")
        domains_file = f"{scraper.results_folder}/{output}"
        scraper.enhanced_analysis_bulk(domains_file)
        print(fg + f"\n🎊 DRAKGRAB SMTP FINISHED! Check {scraper.results_folder}/")
    else:
        print(fr + "❌ No domains scraped. Check cookies.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(fy + "\n⏹️ DRAKGRAB stopped by user.")
    except Exception as e:
        print(fr + f"❌ Error: {e}")
        logging.error(f"Fatal: {e}", exc_info=True)
