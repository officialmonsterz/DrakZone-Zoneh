#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
import subprocess
import threading
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
import psutil

try:
    import playwright.sync_api as playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

try:
    import shodan
    SHODAN_AVAILABLE = True
except ImportError:
    SHODAN_AVAILABLE = False

# Initialize colorama
init(autoreset=True)

# Color shortcuts
fr = Fore.RED
fc = Fore.CYAN
fw = Fore.WHITE
fy = Fore.YELLOW
fg = Fore.GREEN
sd = Style.DIM
sn = Style.NORMAL
sb = Style.BRIGHT

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

class ZoneHScraper:
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
            'shodan_api': '',
            'nuclei_path': 'nuclei',
            'nmap_path': 'nmap',
            'max_threads': 50,
            'scan_timeout': 3,
            'retry_attempts': 3,
            'rate_delay_min': 1,
            'rate_delay_max': 5
        }
        
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                default_config.update(config)
        
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
                logging.FileHandler(f"{log_dir}/drakgrab.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def create_results_folder(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results_folder = f"{self.results_folder}_{timestamp}"
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
        
        # Extract first valid domain
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
    
    def nmap_scan(self, ip):
        try:
            cmd = [self.config['nmap_path'], '-sV', '-T4', '--top-ports', '50', '-oN', '-', ip]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
            return result.stdout if result.returncode == 0 else ""
        except:
            return ""
    
    def nuclei_scan(self, target):
        try:
            cmd = [self.config['nuclei_path'], '-u', target, '-t', 'cves/','misconfiguration/','exposed-panels/','-silent','-oc','-', '-rl', '20']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
            return result.stdout.strip().split('\n') if result.returncode == 0 else []
        except:
            return []
    
    def shodan_lookup(self, ip):
        if not self.config.get('shodan_api') or not SHODAN_AVAILABLE:
            return {}
        try:
            api = shodan.Shodan(self.config['shodan_api'])
            host = api.host(ip)
            return {
                'ports': host.get('ports', []),
                'org': host.get('org', ''),
                'os': host.get('os', '')
            }
        except:
            return {}
    
    def geoip_lookup(self, ip):
        try:
            resp = requests.get(f"http://ip-api.com/json/{ip}?fields=status,message,country,city,org,asn,isp", timeout=8)
            data = resp.json()
            if data['status'] == 'success':
                return data
        except:
            pass
        return {}
    
    def analyze_domain_enhanced(self, domain):
        result = {
            'domain': domain,
            'score': 0,
            'ports': [],
            'services': [],
            'vulns': [],
            'geo': {},
            'shodan': {},
            'status': 'ok'
        }
        
        try:
            # Resolve IP
            try:
                ip = socket.gethostbyname(domain.replace('http://', '').replace('https://', ''))
                result['ip'] = ip
            except:
                result['status'] = 'no-dns'
                return result
            
            # Nmap
            nmap_out = self.nmap_scan(ip)
            if nmap_out:
                ports = re.findall(r'(\d+)/tcp\s+open', nmap_out)
                services = re.findall(r'(\d+)/tcp\s+open\s+(\S+)', nmap_out)
                result['ports'] = [int(p) for p in ports]
                result['services'] = [f"{s[0]}:{s[1]}" for s in services]
            
            # Scoring
            high_value_ports = [2082,2083,2086,2087,3389,21,23]
            if any(p in result['ports'] for p in high_value_ports):
                result['score'] += 20
            if len(result['ports']) > 3:
                result['score'] += 10
            
            # GeoIP
            result['geo'] = self.geoip_lookup(ip)
            
            # Shodan
            result['shodan'] = self.shodan_lookup(ip)
            
            # Nuclei
            result['vulns'] = self.nuclei_scan(domain)
            
        except Exception:
            result['status'] = 'error'
        
        return result
    
    def enhanced_analysis_bulk(self, domains_file):
        print(fy + "🔥 DRAKGRAB ENHANCED ANALYSIS STARTING...")
        
        with open(domains_file, 'r') as f:
            domains = [line.strip().replace('http://','').rstrip('/') for line in f if line.strip()]
        
        domains = list(set(domains))
        print(fg + f"🎯 Analyzing {len(domains)} unique domains...")
        
        results = []
        with ThreadPoolExecutor(max_workers=self.config['max_threads']) as executor:
            future_to_domain = {executor.submit(self.analyze_domain_enhanced, d): d for d in domains}
            
            for i, future in enumerate(as_completed(future_to_domain), 1):
                domain = future_to_domain[future]
                try:
                    result = future.result(timeout=180)
                    results.append(result)
                    
                    score = result.get('score', 0)
                    ports_count = len(result.get('ports', []))
                    color = fg if score >= 10 else fy
                    print(color + f"[{i:3d}/{len(domains)}] {domain[:40]:40} | Score:{score:2d} | Ports:{ports_count}")
                except:
                    print(fr + f"[{i:3d}/{len(domains)}] {domain[:40]:40} | TIMEOUT")
        
        # Sort & Export
        results.sort(key=lambda x: x['score'], reverse=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON
        json_file = f"{self.results_folder}/drakgrab_results_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=1, default=str)
        
        # CSV
        csv_file = f"{self.results_folder}/drakgrab_results_{timestamp}.csv"
        pd.DataFrame(results).to_csv(csv_file, index=False)
        
        # High value
        high_value = [r for r in results if r['score'] >= 10]
        hv_file = f"{self.results_folder}/HIGH_VALUE_TARGETS_{timestamp}.txt"
        with open(hv_file, 'w') as f:
            f.write(f"DRAKGRAB HIGH VALUE TARGETS (Score 10+)\n")
            f.write("="*60 + "\n\n")
            for r in high_value:
                f.write(f"DOMAIN: {r['domain']}\n")
                f.write(f"SCORE: {r['score']}\n")
                f.write(f"IP: {r.get('ip','N/A')}\n")
                f.write(f"PORTS: {', '.join(map(str,r.get('ports',[])))}\n")
                f.write(f"SERVICES: {', '.join(r.get('services',[])[:3])}\n")
                f.write(f"VULNS: {len(r.get('vulns',[]))}\n")
                f.write("-"*60 + "\n\n")
        
        print(fg + f"\n🎉 DRAKGRAB COMPLETE!")
        print(fg + f"📊 JSON: {json_file}")
        print(fg + f"📊 CSV:  {csv_file}")
        print(sb + f"⭐  HIGH VALUE: {hv_file} ({len(high_value)} targets)")
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
{fc}║  {fg}willsmith32701@gmail.com  |  DRAKGRAB 2026  |  Ultimate Zone-H Defacement Hunter  {fc}║
{fc}║  {fg}Nmap • Nuclei • Shodan • GeoIP • AI Analysis • Multi-Threaded • Production Ready   {fc}║
{fc}╚══════════════════════════════════════════════════════════════════════════════════════╝
{sn}
    """
    print(banner)

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def main():
    clear_screen()
    display_banner()
    
    scraper = ZoneHScraper()
    
    print(fc + "\n🎯 DRAKGRAB Zone-H Archive Options:")
    print(fc + "1. Notifier (Hacker ID)")
    print(fc + "2. On-Hold Sites") 
    print(fc + "3. IP Archive")
    print(fc + "4. Tag Search")
    print(fc + "5. Hacker Archive")
    
    choice = input(fy + "Select (1-5): ").strip()
    
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
    
    # Build URL
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
    
    print(fg + f"\n🚀 Starting DRAKGRAB: {url}")
    print(fg + f"📁 Results → {scraper.results_folder}")
    
    domains = scraper.scrape_archive(url, output, cookies, f"mode_{choice}")
    
    if domains:
        print(fg + f"\n✅ Scraped {len(domains)} domains!")
        domains_file = f"{scraper.results_folder}/{output}"
        scraper.enhanced_analysis_bulk(domains_file)
        print(fg + f"\n🎊 DRAKGRAB FINISHED! Check {scraper.results_folder}/")
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
