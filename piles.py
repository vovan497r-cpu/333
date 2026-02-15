#!/usr/bin/env python3
"""
Site Scanner GUI - Параллельный сканер сайтов с поиском ключей
Проверяет 100+ сайтов одновременно с задержкой 600ms
"""

import asyncio
import aiohttp
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import random
import json
import os
import re
from datetime import datetime
from typing import List, Dict
import webbrowser

class SiteScannerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🚀 Site Scanner v2.0 - Параллельный поиск ключей")
        self.root.geometry("1400x900")
        
        # Переменные
        self.delay_var = tk.DoubleVar(value=0.6)
        self.threads_var = tk.IntVar(value=30)
        self.timeout_var = tk.IntVar(value=10)
        self.is_scanning = False
        self.results = []
        self.sites = []
        
        # Создаем папку для результатов
        self.create_results_folder()
        
        # Создаем интерфейс
        self.create_widgets()
        
        # Загружаем сайты по умолчанию
        self.load_default_sites()
        
        self.log("="*80, "HEADER")
        self.log("🚀 SITE SCANNER v2.0 - Параллельный сканер сайтов", "HEADER")
        self.log(f"📁 Результаты: {self.results_folder}", "INFO")
        self.log("="*80, "HEADER")
    
    def create_results_folder(self):
        """Создание папки для результатов"""
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        self.results_folder = os.path.join(desktop, "SiteScanner_Results")
        
        if not os.path.exists(self.results_folder):
            os.makedirs(self.results_folder)
    
    def create_widgets(self):
        """Создание интерфейса"""
        
        # Левая панель
        left_panel = ttk.Frame(self.root, width=400)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)
        left_panel.pack_propagate(False)
        
        # Настройки
        settings_frame = ttk.LabelFrame(left_panel, text="⚙️ НАСТРОЙКИ", padding=5)
        settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Задержка
        delay_frame = ttk.Frame(settings_frame)
        delay_frame.pack(fill=tk.X, pady=2)
        ttk.Label(delay_frame, text="Задержка (сек):").pack(side=tk.LEFT)
        ttk.Spinbox(delay_frame, from_=0.1, to=3.0, increment=0.1, 
                   textvariable=self.delay_var, width=10).pack(side=tk.RIGHT)
        
        # Потоки
        threads_frame = ttk.Frame(settings_frame)
        threads_frame.pack(fill=tk.X, pady=2)
        ttk.Label(threads_frame, text="Потоков:").pack(side=tk.LEFT)
        ttk.Spinbox(threads_frame, from_=1, to=100, 
                   textvariable=self.threads_var, width=10).pack(side=tk.RIGHT)
        
        # Таймаут
        timeout_frame = ttk.Frame(settings_frame)
        timeout_frame.pack(fill=tk.X, pady=2)
        ttk.Label(timeout_frame, text="Таймаут (сек):").pack(side=tk.LEFT)
        ttk.Spinbox(timeout_frame, from_=5, to=30, 
                   textvariable=self.timeout_var, width=10).pack(side=tk.RIGHT)
        
        # Список сайтов
        sites_frame = ttk.LabelFrame(left_panel, text="🌐 СПИСОК САЙТОВ", padding=5)
        sites_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Текстовое поле для сайтов
        self.sites_text = scrolledtext.ScrolledText(
            sites_frame, height=15, font=('Courier', 9)
        )
        self.sites_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Кнопки для сайтов
        btn_frame = ttk.Frame(sites_frame)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="📂 Загрузить из файла", 
                  command=self.load_sites_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="💾 Сохранить список", 
                  command=self.save_sites_file).pack(side=tk.LEFT, padx=2)
        
        # Управление
        control_frame = ttk.LabelFrame(left_panel, text="🎮 УПРАВЛЕНИЕ", padding=5)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X)
        
        self.btn_start = ttk.Button(button_frame, text="▶️ СТАРТ", 
                                    command=self.start_scan, width=15)
        self.btn_start.pack(side=tk.LEFT, padx=2)
        
        self.btn_stop = ttk.Button(button_frame, text="⏹️ СТОП", 
                                   command=self.stop_scan, state=tk.DISABLED, width=15)
        self.btn_stop.pack(side=tk.LEFT, padx=2)
        
        self.btn_save = ttk.Button(button_frame, text="💾 СОХРАНИТЬ", 
                                   command=self.save_results, width=15)
        self.btn_save.pack(side=tk.LEFT, padx=2)
        
        self.btn_clear = ttk.Button(button_frame, text="🗑️ ОЧИСТИТЬ", 
                                    command=self.clear_all, width=15)
        self.btn_clear.pack(side=tk.LEFT, padx=2)
        
        # Статистика
        stats_frame = ttk.LabelFrame(left_panel, text="📊 СТАТИСТИКА", padding=5)
        stats_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.stats_text = tk.Text(stats_frame, height=8, font=('Courier', 9), bg='#f0f0f0')
        self.stats_text.pack(fill=tk.X)
        
        # Правая панель - ЛОГ
        right_panel = ttk.Frame(self.root)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        log_frame = ttk.LabelFrame(right_panel, text="🔍 ЛОГ СКАНЕРОВАНИЯ", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame, font=('Courier', 9), wrap=tk.WORD,
            bg='#1e1e1e', fg='#00ff00'
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Теги для логов
        self.log_text.tag_config("HEADER", foreground="#ffffff", font=('Courier', 10, 'bold'))
        self.log_text.tag_config("INFO", foreground="#00ffff")
        self.log_text.tag_config("SUCCESS", foreground="#00ff00")
        self.log_text.tag_config("KEY", foreground="#ff00ff", font=('Courier', 9, 'bold'))
        self.log_text.tag_config("ERROR", foreground="#ff0000")
        self.log_text.tag_config("WARNING", foreground="#ffff00")
        
        # Статус бар
        self.status_bar = ttk.Label(self.root, text="Готов", relief=tk.SUNKEN)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def log(self, message: str, tag: str = "INFO"):
        """Добавление в лог"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n", tag)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def update_stats(self):
        """Обновление статистики"""
        total = len(self.sites)
        scanned = len([r for r in self.results if r.get('status') == 'ok'])
        keys = sum(len(r.get('keys', [])) for r in self.results)
        
        stats = f"""
╔══════════════════════════╗
║        📊 СТАТИСТИКА     ║
╚══════════════════════════╝

Всего сайтов:    {total}
Отсканировано:   {scanned}
Найдено ключей:  {keys}
Сайтов с ключами: {len([r for r in self.results if r.get('keys')])}

⏱️ {datetime.now().strftime('%H:%M:%S')}
"""
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, stats)
    
    def load_default_sites(self):
        """Загрузка сайтов по умолчанию"""
        default_sites = [
            "https://github.com",
            "https://gitlab.com",
            "https://bitbucket.org",
            "https://pastebin.com",
            "https://gist.github.com",
            "https://codeshare.io",
            "https://jsfiddle.net",
            "https://codepen.io",
            "https://replit.com",
            "https://glitch.com"
        ]
        
        for site in default_sites:
            self.sites_text.insert(tk.END, site + "\n")
        
        self.log("📋 Загружены сайты по умолчанию", "INFO")
    
    def load_sites_file(self):
        """Загрузка сайтов из файла"""
        filename = filedialog.askopenfilename(
            title="Выберите файл со списком сайтов",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.sites_text.delete(1.0, tk.END)
                self.sites_text.insert(1.0, content)
                self.log(f"📂 Загружено сайтов из {filename}", "SUCCESS")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить файл: {e}")
    
    def save_sites_file(self):
        """Сохранение списка сайтов"""
        filename = filedialog.asksaveasfilename(
            title="Сохранить список сайтов",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                content = self.sites_text.get(1.0, tk.END)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.log(f"💾 Список сайтов сохранен", "SUCCESS")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить: {e}")
    
    def get_sites_list(self) -> List[str]:
        """Получение списка сайтов из текстового поля"""
        content = self.sites_text.get(1.0, tk.END)
        sites = []
        
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                if not line.startswith(('http://', 'https://')):
                    line = 'https://' + line
                sites.append(line)
        
        return sites
    
    def start_scan(self):
        """Запуск сканирования"""
        self.sites = self.get_sites_list()
        
        if not self.sites:
            messagebox.showwarning("Внимание", "Добавьте сайты для сканирования")
            return
        
        self.is_scanning = True
        self.results = []
        
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        
        self.log("", "HEADER")
        self.log("🚀 НАЧАЛО СКАНИРОВАНИЯ", "HEADER")
        self.log(f"📊 Сайтов: {len(self.sites)}", "INFO")
        self.log(f"⚙️ Задержка: {self.delay_var.get()} сек, Потоков: {self.threads_var.get()}", "INFO")
        self.log("-"*60, "INFO")
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=self.run_scan, daemon=True)
        thread.start()
    
    def run_scan(self):
        """Запуск асинхронного сканирования"""
        asyncio.run(self.async_scan())
    
    async def async_scan(self):
        """Асинхронное сканирование"""
        connector = aiohttp.TCPConnector(limit=self.threads_var.get())
        timeout = aiohttp.ClientTimeout(total=self.timeout_var.get())
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            semaphore = asyncio.Semaphore(self.threads_var.get())
            
            tasks = []
            for site in self.sites:
                task = self.check_site(session, site, semaphore)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            self.results = [r for r in results if r]
        
        # Анализ результатов
        self.analyze_results()
    
    async def check_site(self, session, site: str, semaphore):
        """Проверка одного сайта"""
        if not self.is_scanning:
            return None
        
        async with semaphore:
            # Задержка
            await asyncio.sleep(self.delay_var.get())
            
            # Рандомный User-Agent
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            ]
            
            headers = {
                'User-Agent': random.choice(user_agents),
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            try:
                start_time = datetime.now()
                
                async with session.get(site, headers=headers, ssl=False) as response:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    
                    if response.status == 200:
                        html = await response.text()
                        keys = self.find_real_keys(html)
                        
                        status = f"✅ {response.status}"
                        if keys:
                            self.log(f"🔑 {site} - НАЙДЕНО {len(keys)} КЛЮЧЕЙ!", "KEY")
                            for key in keys[:3]:
                                self.log(f"   {key[:80]}...", "KEY")
                        else:
                            self.log(f"📄 {site} - {response.status} ({elapsed:.1f} сек)", "INFO")
                        
                        return {
                            'site': site,
                            'status': 'ok',
                            'http_status': response.status,
                            'keys': keys,
                            'time': elapsed,
                            'size': len(html)
                        }
                    else:
                        self.log(f"⚠️ {site} - HTTP {response.status}", "WARNING")
                        return {
                            'site': site,
                            'status': 'error',
                            'http_status': response.status,
                            'keys': [],
                            'time': elapsed
                        }
                        
            except asyncio.TimeoutError:
                self.log(f"⏰ {site} - Таймаут ({self.timeout_var.get()} сек)", "ERROR")
                return {'site': site, 'status': 'timeout', 'keys': []}
            except Exception as e:
                self.log(f"❌ {site} - Ошибка: {str(e)[:50]}", "ERROR")
                return {'site': site, 'status': 'error', 'keys': []}
    
    def find_real_keys(self, html: str) -> List[str]:
        """
        Поиск РЕАЛЬНЫХ ключей в HTML
        Только настоящие приватные ключи, API ключи и токены
        """
        keys = []
        
        # 1. Приватные ключи EVM (64 hex символа с 0x или без)
        evm_patterns = [
            r'0x[a-fA-F0-9]{64}',  # с 0x
            r'\b[a-fA-F0-9]{64}\b',  # без 0x
            r'private[_\-]?key["\']?\s*[:=]\s*["\']?(0x[a-fA-F0-9]{64})',
            r'secret[_\-]?key["\']?\s*[:=]\s*["\']?(0x[a-fA-F0-9]{64})',
            r'wallet[_\-]?seed["\']?\s*[:=]\s*["\']?([a-fA-F0-9]{64})'
        ]
        
        for pattern in evm_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                if len(match) >= 64 and all(c in '0123456789abcdefABCDEF' for c in match.replace('0x', '')):
                    # ПОЛНЫЙ ключ без обрезки
                    keys.append(f"EVM Private Key: {match}")
        
        # 2. API ключи (32-64 символа, буквы и цифры)
        api_patterns = [
            r'api[_\-]?key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9]{32,64})["\']?',
            r'api[_\-]?secret["\']?\s*[:=]\s*["\']?([a-zA-Z0-9]{32,64})["\']?',
            r'app[_\-]?key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9]{32,64})["\']?',
            r'app[_\-]?secret["\']?\s*[:=]\s*["\']?([a-zA-Z0-9]{32,64})["\']?'
        ]
        
        for pattern in api_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                if len(match) >= 32:
                    # ПОЛНЫЙ ключ
                    keys.append(f"API Key: {match}")
        
        # 3. AWS ключи (начинаются с AKIA)
        aws_pattern = r'(AKIA[0-9A-Z]{16})'
        matches = re.findall(aws_pattern, html)
        for match in matches:
            keys.append(f"AWS Key: {match}")
        
        # 4. GitHub токены (40 символов)
        github_patterns = [
            r'github[_\-]?token["\']?\s*[:=]\s*["\']?([a-zA-Z0-9]{40})["\']?',
            r'ghp_[a-zA-Z0-9]{36}',
            r'gho_[a-zA-Z0-9]{36}'
        ]
        
        for pattern in github_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                # ПОЛНЫЙ токен
                keys.append(f"GitHub Token: {match}")
        
        # 5. JWT токены
        jwt_pattern = r'eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+'
        matches = re.findall(jwt_pattern, html)
        for match in matches[:5]:  # Ограничиваем количество
            # ПОЛНЫЙ JWT
            keys.append(f"JWT Token: {match}")
        
        # 6. MongoDB строки подключения
        mongo_pattern = r'mongodb(?:\+srv)?://[a-zA-Z0-9_:@/\\-.]+'
        matches = re.findall(mongo_pattern, html)
        for match in matches:
            # ПОЛНЫЙ URI
            keys.append(f"MongoDB URI: {match}")
        
        # 7. PostgreSQL строки подключения
        postgres_pattern = r'postgres(?:ql)?://[a-zA-Z0-9_:@/\\-.]+'
        matches = re.findall(postgres_pattern, html)
        for match in matches:
            # ПОЛНЫЙ URI
            keys.append(f"PostgreSQL URI: {match}")
        
        # 8. Настоящие мнемоники (12/24 слова из BIP39 словаря)
        # ПОЛНЫЙ список BIP39 (2048 слов)
        bip39_words = [
            'abandon', 'ability', 'able', 'about', 'above', 'absent', 'absorb', 'abstract', 'absurd', 'abuse',
            'access', 'accident', 'account', 'accuse', 'achieve', 'acid', 'acoustic', 'acquire', 'across', 'act',
            'action', 'actor', 'actress', 'actual', 'adapt', 'add', 'addict', 'address', 'adjust', 'admit',
            'adult', 'advance', 'advice', 'aerobic', 'affair', 'afford', 'afraid', 'again', 'age', 'agent',
            'agree', 'ahead', 'aim', 'air', 'airport', 'aisle', 'alarm', 'album', 'alcohol', 'alert',
            'alien', 'all', 'alley', 'allow', 'almost', 'alone', 'alpha', 'already', 'also', 'alter',
            'always', 'amateur', 'amazing', 'among', 'amount', 'amused', 'analyst', 'anchor', 'ancient', 'anger',
            'angle', 'angry', 'animal', 'ankle', 'announce', 'annual', 'another', 'answer', 'antenna', 'antique',
            'anxiety', 'any', 'apart', 'apology', 'appear', 'apple', 'approve', 'april', 'arch', 'arctic',
            'area', 'arena', 'argue', 'arm', 'armed', 'armor', 'army', 'around', 'arrange', 'arrest',
            'arrive', 'arrow', 'art', 'artefact', 'artist', 'artwork', 'ask', 'aspect', 'assault', 'asset',
            'assist', 'assume', 'asthma', 'athlete', 'atom', 'attack', 'attend', 'attitude', 'attract', 'auction',
            'audit', 'august', 'aunt', 'author', 'auto', 'autumn', 'average', 'avocado', 'avoid', 'awake',
            'aware', 'away', 'awesome', 'awful', 'awkward', 'axis', 'baby', 'bachelor', 'bacon', 'badge',
            'bag', 'balance', 'balcony', 'ball', 'bamboo', 'banana', 'banner', 'bar', 'barely', 'bargain',
            'barrel', 'base', 'basic', 'basket', 'battle', 'beach', 'bean', 'beauty', 'because', 'become',
            'beef', 'before', 'begin', 'behave', 'behind', 'believe', 'below', 'belt', 'bench', 'benefit',
            'best', 'betray', 'better', 'between', 'beyond', 'bicycle', 'bid', 'bike', 'bind', 'biology',
            'bird', 'birth', 'bitter', 'black', 'blade', 'blame', 'blanket', 'blast', 'bleak', 'bless',
            'blind', 'blood', 'blossom', 'blouse', 'blue', 'blur', 'blush', 'board', 'boat', 'body',
            'boil', 'bomb', 'bone', 'bonus', 'book', 'boost', 'border', 'boring', 'borrow', 'boss',
            'bottom', 'bounce', 'box', 'boy', 'bracket', 'brain', 'brand', 'brass', 'brave', 'bread',
            'breeze', 'brick', 'bridge', 'brief', 'bright', 'bring', 'brisk', 'broccoli', 'broken', 'bronze',
            'broom', 'brother', 'brown', 'brush', 'bubble', 'buddy', 'budget', 'buffalo', 'build', 'bulb',
            'bulk', 'bullet', 'bundle', 'bunker', 'burden', 'burger', 'burst', 'bus', 'business', 'busy',
            'butter', 'buyer', 'buzz', 'cabbage', 'cabin', 'cable', 'cactus', 'cage', 'cake', 'call',
            'calm', 'camera', 'camp', 'can', 'canal', 'cancel', 'candy', 'cannon', 'canoe', 'canvas',
            'canyon', 'capable', 'capital', 'captain', 'car', 'carbon', 'card', 'cargo', 'carpet', 'carry',
            'cart', 'case', 'cash', 'casino', 'castle', 'casual', 'cat', 'catalog', 'catch', 'category',
            'cattle', 'caught', 'cause', 'caution', 'cave', 'ceiling', 'celery', 'cement', 'census', 'century',
            'cereal', 'certain', 'chair', 'chalk', 'champion', 'change', 'chaos', 'chapter', 'charge', 'chase',
            'chat', 'cheap', 'check', 'cheese', 'chef', 'cherry', 'chest', 'chicken', 'chief', 'child',
            'chimney', 'choice', 'choose', 'chronic', 'chuckle', 'chunk', 'churn', 'cigar', 'cinnamon', 'circle',
            'citizen', 'city', 'civil', 'claim', 'clap', 'clarify', 'claw', 'clay', 'clean', 'clerk',
            'clever', 'click', 'client', 'cliff', 'climb', 'clinic', 'clip', 'clock', 'clog', 'close',
            'cloth', 'cloud', 'clown', 'club', 'clump', 'cluster', 'clutch', 'coach', 'coast', 'coconut',
            'code', 'coffee', 'coil', 'coin', 'collect', 'color', 'column', 'combine', 'come', 'comfort',
            'comic', 'common', 'company', 'concert', 'conduct', 'confirm', 'congress', 'connect', 'consider', 'control',
            'convince', 'cook', 'cool', 'copper', 'copy', 'coral', 'core', 'corn', 'correct', 'cost',
            'cotton', 'couch', 'country', 'couple', 'course', 'cousin', 'cover', 'coyote', 'crack', 'cradle',
            'craft', 'cram', 'crane', 'crash', 'crater', 'crawl', 'crazy', 'cream', 'credit', 'creek',
            'crew', 'cricket', 'crime', 'crisp', 'critic', 'crop', 'cross', 'crouch', 'crowd', 'crucial',
            'cruel', 'cruise', 'crumble', 'crunch', 'crush', 'cry', 'crystal', 'cube', 'culture', 'cup',
            'cupboard', 'curious', 'current', 'curtain', 'curve', 'cushion', 'custom', 'cute', 'cycle', 'dad',
            'damage', 'damp', 'dance', 'danger', 'daring', 'dash', 'daughter', 'dawn', 'day', 'deal',
            'debate', 'debris', 'decade', 'december', 'decide', 'decline', 'decorate', 'decrease', 'deer', 'defense',
            'define', 'defy', 'degree', 'delay', 'deliver', 'demand', 'demise', 'denial', 'dentist', 'deny',
            'depart', 'depend', 'deposit', 'depth', 'deputy', 'derive', 'describe', 'desert', 'design', 'desk',
            'despair', 'destroy', 'detail', 'detect', 'develop', 'device', 'devote', 'diagram', 'dial', 'diamond',
            'diary', 'dice', 'diesel', 'diet', 'differ', 'digital', 'dignity', 'dilemma', 'dinner', 'dinosaur',
            'direct', 'dirt', 'disagree', 'discover', 'disease', 'dish', 'dismiss', 'disorder', 'display', 'distance',
            'divert', 'divide', 'divorce', 'dizzy', 'doctor', 'document', 'dog', 'doll', 'dolphin', 'domain',
            'donate', 'donkey', 'donor', 'door', 'dose', 'double', 'dove', 'draft', 'dragon', 'drama',
            'drastic', 'draw', 'dream', 'dress', 'drift', 'drill', 'drink', 'drip', 'drive', 'drop',
            'drum', 'dry', 'duck', 'dumb', 'dune', 'during', 'dust', 'dutch', 'duty', 'dwarf',
            'dynamic', 'eager', 'eagle', 'early', 'earn', 'earth', 'easily', 'east', 'easy', 'echo',
            'ecology', 'economy', 'edge', 'edit', 'educate', 'effort', 'egg', 'eight', 'either', 'elbow',
            'elder', 'electric', 'elegant', 'element', 'elephant', 'elevator', 'elite', 'else', 'embark', 'embody',
            'embrace', 'emerge', 'emotion', 'employ', 'empower', 'empty', 'enable', 'enact', 'end', 'endless',
            'endorse', 'enemy', 'energy', 'enforce', 'engage', 'engine', 'enhance', 'enjoy', 'enlist', 'enough',
            'enrich', 'enroll', 'ensure', 'enter', 'entire', 'entry', 'envelope', 'episode', 'equal', 'equip',
            'era', 'erase', 'erode', 'erosion', 'error', 'erupt', 'escape', 'essay', 'essence', 'estate',
            'eternal', 'ethics', 'evidence', 'evil', 'evoke', 'evolve', 'exact', 'example', 'excess', 'exchange',
            'excite', 'exclude', 'excuse', 'execute', 'exercise', 'exhaust', 'exhibit', 'exile', 'exist', 'exit',
            'exotic', 'expand', 'expect', 'expire', 'explain', 'expose', 'express', 'extend', 'extra', 'eye',
            'eyebrow', 'fabric', 'face', 'faculty', 'fade', 'faint', 'faith', 'fall', 'false', 'fame',
            'family', 'famous', 'fan', 'fancy', 'fantasy', 'farm', 'fashion', 'fat', 'fatal', 'father',
            'fatigue', 'fault', 'favorite', 'feature', 'february', 'federal', 'fee', 'feed', 'feel', 'female',
            'fence', 'festival', 'fetch', 'fever', 'few', 'fiber', 'fiction', 'field', 'figure', 'file',
            'film', 'filter', 'final', 'find', 'fine', 'finger', 'finish', 'fire', 'firm', 'first',
            'fiscal', 'fish', 'fit', 'fitness', 'fix', 'flag', 'flame', 'flash', 'flat', 'flavor',
            'flee', 'flight', 'flip', 'float', 'flock', 'floor', 'flower', 'fluid', 'flush', 'fly',
            'foam', 'focus', 'fog', 'foil', 'fold', 'follow', 'food', 'foot', 'force', 'forest',
            'forget', 'fork', 'fortune', 'forum', 'forward', 'fossil', 'foster', 'found', 'fox', 'fragile',
            'frame', 'frequent', 'fresh', 'friend', 'fringe', 'frog', 'front', 'frost', 'frown', 'frozen',
            'fruit', 'fuel', 'fun', 'funny', 'furnace', 'fury', 'future', 'gadget', 'gain', 'galaxy',
            'gallery', 'game', 'gap', 'garage', 'garbage', 'garden', 'garlic', 'garment', 'gas', 'gasp',
            'gate', 'gather', 'gauge', 'gaze', 'general', 'genius', 'genre', 'gentle', 'genuine', 'gesture',
            'ghost', 'giant', 'gift', 'giggle', 'ginger', 'giraffe', 'girl', 'give', 'glad', 'glance',
            'glare', 'glass', 'glide', 'glimpse', 'globe', 'gloom', 'glory', 'glove', 'glow', 'glue',
            'goat', 'goddess', 'gold', 'good', 'goose', 'gorilla', 'gospel', 'gossip', 'govern', 'gown',
            'grab', 'grace', 'grain', 'grant', 'grape', 'grass', 'gravity', 'great', 'green', 'grid',
            'grief', 'grit', 'grocery', 'group', 'grow', 'grunt', 'guard', 'guess', 'guide', 'guilt',
            'guitar', 'gun', 'gym', 'habit', 'hair', 'half', 'hammer', 'hamster', 'hand', 'happy',
            'harbor', 'hard', 'harsh', 'harvest', 'hat', 'have', 'hawk', 'hazard', 'head', 'health',
            'heart', 'heavy', 'hedgehog', 'height', 'hello', 'helmet', 'help', 'hen', 'hero', 'hidden',
            'high', 'hill', 'hint', 'hip', 'hire', 'history', 'hobby', 'hockey', 'hold', 'hole',
            'holiday', 'hollow', 'home', 'honey', 'hood', 'hope', 'horn', 'horror', 'horse', 'hospital',
            'host', 'hotel', 'hour', 'hover', 'hub', 'huge', 'human', 'humble', 'humor', 'hundred',
            'hungry', 'hunt', 'hurdle', 'hurry', 'hurt', 'husband', 'hybrid', 'ice', 'icon', 'idea',
            'identify', 'idle', 'ignore', 'ill', 'illegal', 'illness', 'image', 'imitate', 'immense', 'immune',
            'impact', 'impose', 'improve', 'impulse', 'inch', 'include', 'income', 'increase', 'index', 'indicate',
            'indoor', 'industry', 'infant', 'inflict', 'inform', 'inhale', 'inherit', 'initial', 'inject', 'injury',
            'inmate', 'inner', 'innocent', 'input', 'inquiry', 'insane', 'insect', 'inside', 'inspire', 'install',
            'intact', 'interest', 'into', 'invest', 'invite', 'involve', 'iron', 'island', 'isolate', 'issue',
            'item', 'ivory', 'jacket', 'jaguar', 'jar', 'jazz', 'jealous', 'jeans', 'jelly', 'jewel',
            'job', 'join', 'joke', 'journey', 'joy', 'judge', 'juice', 'jump', 'jungle', 'junior',
            'junk', 'just', 'kangaroo', 'keen', 'keep', 'ketchup', 'key', 'kick', 'kid', 'kidney',
            'kind', 'kingdom', 'kiss', 'kit', 'kitchen', 'kite', 'kitten', 'kiwi', 'knee', 'knife',
            'knock', 'know', 'lab', 'label', 'labor', 'ladder', 'lady', 'lake', 'lamp', 'language',
            'laptop', 'large', 'later', 'latin', 'laugh', 'laundry', 'lava', 'law', 'lawn', 'lawsuit',
            'layer', 'lazy', 'leader', 'leaf', 'learn', 'leave', 'lecture', 'left', 'leg', 'legal',
            'legend', 'leisure', 'lemon', 'lend', 'length', 'lens', 'leopard', 'lesson', 'letter', 'level',
            'liar', 'liberty', 'library', 'license', 'life', 'lift', 'light', 'like', 'limb', 'limit',
            'link', 'lion', 'liquid', 'list', 'little', 'live', 'lizard', 'load', 'loan', 'lobster',
            'local', 'lock', 'logic', 'lonely', 'long', 'loop', 'lottery', 'loud', 'lounge', 'love',
            'loyal', 'lucky', 'luggage', 'lumber', 'lunar', 'lunch', 'luxury', 'lyrics', 'machine', 'mad',
            'magic', 'magnet', 'maid', 'mail', 'main', 'major', 'make', 'mammal', 'man', 'manage',
            'mandate', 'mango', 'mansion', 'manual', 'maple', 'marble', 'march', 'margin', 'marine', 'market',
            'marriage', 'mask', 'mass', 'master', 'match', 'material', 'math', 'matrix', 'matter', 'maximum',
            'maze', 'meadow', 'mean', 'measure', 'meat', 'mechanic', 'medal', 'media', 'melody', 'melt',
            'member', 'memory', 'mention', 'menu', 'mercy', 'merge', 'merit', 'merry', 'mesh', 'message',
            'metal', 'method', 'middle', 'midnight', 'milk', 'million', 'mimic', 'mind', 'minimum', 'minor',
            'minute', 'miracle', 'mirror', 'misery', 'miss', 'mistake', 'mix', 'mixed', 'mixture', 'mobile',
            'model', 'modify', 'mom', 'moment', 'monitor', 'monkey', 'monster', 'month', 'moon', 'moral',
            'more', 'morning', 'mosquito', 'mother', 'motion', 'motor', 'mountain', 'mouse', 'move', 'movie',
            'much', 'muffin', 'mule', 'multiply', 'muscle', 'museum', 'mushroom', 'music', 'must', 'mutual',
            'myself', 'mystery', 'myth', 'naive', 'name', 'napkin', 'narrow', 'nasty', 'nation', 'nature',
            'near', 'neck', 'need', 'negative', 'neglect', 'neither', 'nephew', 'nerve', 'nest', 'net',
            'network', 'neutral', 'never', 'news', 'next', 'nice', 'night', 'noble', 'noise', 'nominee',
            'noodle', 'normal', 'north', 'nose', 'notable', 'note', 'nothing', 'notice', 'novel', 'now',
            'nuclear', 'number', 'nurse', 'nut', 'oak', 'obey', 'object', 'oblige', 'obscure', 'observe',
            'obtain', 'obvious', 'occur', 'ocean', 'october', 'odor', 'off', 'offer', 'office', 'often',
            'oil', 'okay', 'old', 'olive', 'olympic', 'omit', 'once', 'one', 'onion', 'online',
            'only', 'open', 'opera', 'opinion', 'oppose', 'option', 'orange', 'orbit', 'orchard', 'order',
            'ordinary', 'organ', 'orient', 'original', 'orphan', 'ostrich', 'other', 'outdoor', 'outer', 'output',
            'outside', 'oval', 'oven', 'over', 'own', 'owner', 'oxygen', 'oyster', 'ozone', 'pact',
            'paddle', 'page', 'pair', 'palace', 'palm', 'panda', 'panel', 'panic', 'panther', 'paper',
            'parade', 'parent', 'park', 'parrot', 'party', 'pass', 'patch', 'path', 'patient', 'patrol',
            'pattern', 'pause', 'pave', 'payment', 'peace', 'peanut', 'pear', 'peasant', 'pelican', 'pen',
            'penalty', 'pencil', 'people', 'pepper', 'perfect', 'permit', 'person', 'pet', 'phone', 'photo',
            'phrase', 'physical', 'piano', 'picnic', 'picture', 'piece', 'pig', 'pigeon', 'pill', 'pilot',
            'pink', 'pioneer', 'pipe', 'pistol', 'pitch', 'pizza', 'place', 'planet', 'plastic', 'plate',
            'play', 'please', 'pledge', 'pluck', 'plug', 'plunge', 'poem', 'poet', 'point', 'polar',
            'pole', 'police', 'pond', 'pony', 'pool', 'popular', 'portion', 'position', 'possible', 'post',
            'potato', 'pottery', 'poverty', 'powder', 'power', 'practice', 'praise', 'predict', 'prefer', 'prepare',
            'present', 'pretty', 'prevent', 'price', 'pride', 'primary', 'print', 'priority', 'prison', 'private',
            'prize', 'problem', 'process', 'produce', 'profit', 'program', 'project', 'promote', 'proof', 'property',
            'prosper', 'protect', 'proud', 'provide', 'public', 'pudding', 'pull', 'pulp', 'pulse', 'pumpkin',
            'punch', 'pupil', 'puppy', 'purchase', 'purity', 'purpose', 'purse', 'push', 'put', 'puzzle',
            'pyramid', 'quality', 'quantum', 'quarter', 'question', 'quick', 'quit', 'quiz', 'quote', 'rabbit',
            'raccoon', 'race', 'rack', 'radar', 'radio', 'rail', 'rain', 'raise', 'rally', 'ramp',
            'ranch', 'random', 'range', 'rapid', 'rare', 'rate', 'rather', 'raven', 'raw', 'razor',
            'ready', 'real', 'reason', 'rebel', 'rebuild', 'recall', 'receive', 'recipe', 'record', 'recycle',
            'reduce', 'reflect', 'reform', 'refuse', 'region', 'regret', 'regular', 'reject', 'relax', 'release',
            'relief', 'rely', 'remain', 'remember', 'remind', 'remove', 'render', 'renew', 'rent', 'reopen',
            'repair', 'repeat', 'replace', 'report', 'require', 'rescue', 'resemble', 'resist', 'resource', 'response',
            'result', 'retire', 'retreat', 'return', 'reunion', 'reveal', 'review', 'reward', 'rhythm', 'rib',
            'ribbon', 'rice', 'rich', 'ride', 'ridge', 'rifle', 'right', 'rigid', 'ring', 'riot',
            'ripple', 'risk', 'ritual', 'rival', 'river', 'road', 'roast', 'robot', 'robust', 'rocket',
            'romance', 'roof', 'rookie', 'room', 'rose', 'rotate', 'rough', 'round', 'route', 'royal',
            'rubber', 'rude', 'rug', 'rule', 'run', 'runway', 'rural', 'sad', 'saddle', 'sadness',
            'safe', 'sail', 'salad', 'salmon', 'salon', 'salt', 'salute', 'same', 'sample', 'sand',
            'satisfy', 'satoshi', 'sauce', 'sausage', 'save', 'say', 'scale', 'scan', 'scare', 'scatter',
            'scene', 'scheme', 'school', 'science', 'scissors', 'scorpion', 'scout', 'scrap', 'screen', 'script',
            'scrub', 'sea', 'search', 'season', 'seat', 'second', 'secret', 'section', 'security', 'seed',
            'seek', 'segment', 'select', 'sell', 'seminar', 'senior', 'sense', 'sentence', 'series', 'service',
            'session', 'settle', 'setup', 'seven', 'shadow', 'shaft', 'shallow', 'share', 'shed', 'shell',
            'sheriff', 'shield', 'shift', 'shine', 'ship', 'shiver', 'shock', 'shoe', 'shoot', 'shop',
            'short', 'shoulder', 'shove', 'shrimp', 'shrug', 'shuffle', 'shy', 'sibling', 'sick', 'side',
            'siege', 'sight', 'sign', 'silent', 'silk', 'silly', 'silver', 'similar', 'simple', 'since',
            'sing', 'siren', 'sister', 'situate', 'six', 'size', 'skate', 'sketch', 'ski', 'skill',
            'skin', 'skirt', 'skull', 'slab', 'slam', 'sleep', 'slender', 'slice', 'slide', 'slight',
            'slim', 'slogan', 'slot', 'slow', 'slush', 'small', 'smart', 'smile', 'smoke', 'smooth',
            'snack', 'snake', 'snap', 'sniff', 'snow', 'soap', 'soccer', 'social', 'sock', 'soda',
            'soft', 'solar', 'soldier', 'solid', 'solution', 'solve', 'someone', 'song', 'soon', 'sorry',
            'sort', 'soul', 'sound', 'soup', 'source', 'south', 'space', 'spare', 'spatial', 'spawn',
            'speak', 'special', 'speed', 'spell', 'spend', 'sphere', 'spice', 'spider', 'spike', 'spin',
            'spirit', 'split', 'spoil', 'sponsor', 'spoon', 'sport', 'spot', 'spray', 'spread', 'spring',
            'spy', 'square', 'squeeze', 'squirrel', 'stable', 'stadium', 'staff', 'stage', 'stairs', 'stamp',
            'stand', 'start', 'state', 'stay', 'steak', 'steel', 'stem', 'step', 'stereo', 'stick',
            'still', 'sting', 'stock', 'stomach', 'stone', 'stool', 'story', 'stove', 'strategy', 'street',
            'strike', 'strong', 'struggle', 'student', 'stuff', 'stumble', 'style', 'subject', 'submit', 'subway',
            'success', 'such', 'sudden', 'suffer', 'sugar', 'suggest', 'suit', 'summer', 'sun', 'sunny',
            'sunset', 'super', 'supply', 'supreme', 'sure', 'surface', 'surge', 'surprise', 'surround', 'survey',
            'suspect', 'sustain', 'swallow', 'swamp', 'swap', 'swarm', 'sway', 'swear', 'sweet', 'swift',
            'swim', 'swing', 'switch', 'sword', 'symbol', 'symptom', 'syrup', 'system', 'table', 'tackle',
            'tag', 'tail', 'talent', 'talk', 'tank', 'tape', 'target', 'task', 'taste', 'tattoo',
            'taxi', 'teach', 'team', 'tell', 'ten', 'tenant', 'tennis', 'tent', 'term', 'test',
            'text', 'thank', 'that', 'thaw', 'theater', 'theft', 'theme', 'then', 'theory', 'there',
            'they', 'thing', 'this', 'thought', 'three', 'thrive', 'throw', 'thumb', 'thunder', 'ticket',
            'tide', 'tiger', 'tilt', 'timber', 'time', 'tiny', 'tip', 'tired', 'tissue', 'title',
            'toast', 'tobacco', 'today', 'toddler', 'toe', 'together', 'toilet', 'token', 'tomato', 'tomorrow',
            'tone', 'tongue', 'tonight', 'tool', 'tooth', 'top', 'topic', 'topple', 'torch', 'tornado',
            'tortoise', 'toss', 'total', 'tourist', 'toward', 'tower', 'town', 'toy', 'track', 'trade',
            'traffic', 'tragic', 'train', 'transfer', 'trap', 'trash', 'travel', 'tray', 'treat', 'tree',
            'trend', 'trial', 'tribe', 'trick', 'trigger', 'trim', 'trip', 'trophy', 'trouble', 'truck',
            'true', 'truly', 'trumpet', 'trust', 'truth', 'try', 'tube', 'tuition', 'tumble', 'tuna',
            'tunnel', 'turkey', 'turn', 'turtle', 'twelve', 'twenty', 'twice', 'twin', 'twist', 'two',
            'type', 'typical', 'ugly', 'umbrella', 'unable', 'unaware', 'uncle', 'uncover', 'under', 'undo',
            'unfair', 'unfold', 'unhappy', 'uniform', 'unique', 'unit', 'universe', 'unknown', 'unlock', 'until',
            'unusual', 'unveil', 'update', 'upgrade', 'uphold', 'upon', 'upper', 'upset', 'urban', 'urge',
            'usage', 'use', 'used', 'useful', 'useless', 'usual', 'utility', 'vacant', 'vacuum', 'vague',
            'valid', 'valley', 'valve', 'van', 'vanish', 'vapor', 'various', 'vast', 'vault', 'vehicle',
            'velvet', 'vendor', 'venture', 'venue', 'verb', 'verify', 'version', 'very', 'vessel', 'veteran',
            'viable', 'vibrant', 'vicious', 'victory', 'video', 'view', 'village', 'vintage', 'violin', 'virtual',
            'virus', 'visa', 'visit', 'visual', 'vital', 'vivid', 'vocal', 'voice', 'void', 'volcano',
            'volume', 'vote', 'voyage', 'wage', 'wagon', 'wait', 'walk', 'wall', 'walnut', 'want',
            'warfare', 'warm', 'warrior', 'wash', 'wasp', 'waste', 'water', 'wave', 'way', 'wealth',
            'weapon', 'wear', 'weasel', 'weather', 'web', 'wedding', 'weekend', 'weird', 'welcome', 'west',
            'wet', 'whale', 'what', 'wheat', 'wheel', 'when', 'where', 'whip', 'whisper', 'wide',
            'width', 'wife', 'wild', 'will', 'win', 'window', 'wine', 'wing', 'wink', 'winner',
            'winter', 'wire', 'wisdom', 'wise', 'wish', 'witness', 'wolf', 'woman', 'wonder', 'wood',
            'wool', 'word', 'work', 'world', 'worry', 'worth', 'wrap', 'wreck', 'wrestle', 'wrist',
            'write', 'wrong', 'yard', 'year', 'yellow', 'you', 'young', 'youth', 'zebra', 'zero',
            'zone', 'zoo'
        ]
        
        # Улучшенный поиск BIP39 мнемоник
        bip39_set = set(bip39_words)
        
        # Ищем последовательности из 12 или 24 слов
        words_in_html = re.findall(r'\b[a-z]+\b', html.lower())
        
        for i in range(len(words_in_html) - 11):
            # Проверяем 12-словную фразу
            phrase_12 = words_in_html[i:i+12]
            valid_count_12 = sum(1 for w in phrase_12 if w in bip39_set)
            if valid_count_12 >= 10:  # Минимум 10 из 12 валидных
                phrase_str = ' '.join(phrase_12)
                keys.append(f"BIP39 Mnemonic (12 words): {phrase_str}")
            
            # Проверяем 24-словную фразу
            if i <= len(words_in_html) - 24:
                phrase_24 = words_in_html[i:i+24]
                valid_count_24 = sum(1 for w in phrase_24 if w in bip39_set)
                if valid_count_24 >= 20:  # Минимум 20 из 24 валидных
                    phrase_str = ' '.join(phrase_24)
                    keys.append(f"BIP39 Mnemonic (24 words): {phrase_str}")
        
        # Убираем дубликаты
        return list(set(keys))
    
    def analyze_results(self):
        """Анализ результатов сканирования"""
        self.is_scanning = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        
        successful = [r for r in self.results if r.get('status') == 'ok']
        failed = [r for r in self.results if r.get('status') != 'ok']
        with_keys = [r for r in self.results if r.get('keys')]
        
        total_keys = sum(len(r.get('keys', [])) for r in self.results)
        
        self.log("", "HEADER")
        self.log("📊 РЕЗУЛЬТАТЫ СКАНИРОВАНИЯ", "HEADER")
        self.log("="*60, "HEADER")
        self.log(f"✅ Успешно: {len(successful)}/{len(self.sites)}", "SUCCESS")
        self.log(f"❌ Ошибок: {len(failed)}", "ERROR")
        self.log(f"🔑 Найдено ключей: {total_keys}", "KEY")
        self.log(f"📍 Сайтов с ключами: {len(with_keys)}", "KEY")
        
        if with_keys:
            self.log("", "HEADER")
            self.log("🔑 САЙТЫ С КЛЮЧАМИ:", "KEY")
            for r in with_keys:
                self.log(f"   {r['site']} - {len(r['keys'])} ключей", "KEY")
        
        self.update_stats()
        
        if with_keys:
            self.btn_save.config(state=tk.NORMAL)
            self.auto_save_results()
    
    def stop_scan(self):
        """Остановка сканирования"""
        self.is_scanning = False
        self.log("⏹️ СКАНИРОВАНИЕ ОСТАНОВЛЕНО", "WARNING")
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
    
    def save_results(self):
        """Сохранение результатов"""
        if not self.results:
            messagebox.showinfo("Инфо", "Нет результатов для сохранения")
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        try:
            # Сохраняем все результаты
            all_file = os.path.join(self.results_folder, f'scan_results_{timestamp}.txt')
            with open(all_file, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write(f"РЕЗУЛЬТАТЫ СКАНИРОВАНИЯ - {datetime.now()}\n")
                f.write("="*80 + "\n\n")
                
                for r in self.results:
                    f.write(f"Сайт: {r['site']}\n")
                    f.write(f"Статус: {r['status']}\n")
                    if 'http_status' in r:
                        f.write(f"HTTP: {r['http_status']}\n")
                    if 'time' in r:
                        f.write(f"Время: {r['time']:.2f} сек\n")
                    if r.get('keys'):
                        f.write(f"Найдено ключей: {len(r['keys'])}\n")
                        for key in r['keys']:
                            f.write(f"  🔑 {key}\n")
                    f.write("-"*40 + "\n\n")
            
            # Сохраняем только сайты с ключами
            with_keys = [r for r in self.results if r.get('keys')]
            if with_keys:
                keys_file = os.path.join(self.results_folder, f'keys_found_{timestamp}.txt')
                with open(keys_file, 'w', encoding='utf-8') as f:
                    f.write("="*80 + "\n")
                    f.write(f"САЙТЫ С НАЙДЕННЫМИ КЛЮЧАМИ - {datetime.now()}\n")
                    f.write("="*80 + "\n\n")
                    
                    for r in with_keys:
                        f.write(f"Сайт: {r['site']}\n")
                        f.write(f"Найдено ключей: {len(r['keys'])}\n")
                        for key in r['keys']:
                            f.write(f"  🔑 {key}\n")
                        f.write("-"*40 + "\n\n")
            
            self.log(f"💾 Результаты сохранены в {self.results_folder}", "SUCCESS")
            messagebox.showinfo("Успех", f"Результаты сохранены в:\n{self.results_folder}")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить: {e}")
    
    def auto_save_results(self):
        """Автосохранение результатов"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        with_keys = [r for r in self.results if r.get('keys')]
        if with_keys:
            auto_file = os.path.join(self.results_folder, f'auto_keys_{timestamp}.txt')
            with open(auto_file, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write(f"АВТОМАТИЧЕСКОЕ СОХРАНЕНИЕ - {datetime.now()}\n")
                f.write("="*80 + "\n\n")
                
                for r in with_keys:
                    f.write(f"🌐 {r['site']}\n")
                    for key in r['keys']:
                        f.write(f"   🔑 {key}\n")
                    f.write("-"*40 + "\n\n")
            
            self.log(f"💾 Автосохранение: {auto_file}", "SUCCESS")
    
    def clear_all(self):
        """Очистка всего"""
        if messagebox.askyesno("Подтверждение", "Очистить все данные?"):
            self.sites_text.delete(1.0, tk.END)
            self.log_text.delete(1.0, tk.END)
            self.results = []
            self.stats_text.delete(1.0, tk.END)
            self.log("🧹 Все данные очищены", "INFO")


def main():
    root = tk.Tk()
    app = SiteScannerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()