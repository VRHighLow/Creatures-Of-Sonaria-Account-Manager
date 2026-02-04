import json
import os
from pathlib import Path
from typing import List, Dict

class Account:
    def __init__(self, username: str, password: str, is_main: bool = False):
        self.username = username
        self.password = password
        self.is_main = is_main
        self.status = "offline"  # offline, launching, online, error
    
    def to_dict(self):
        return {
            "username": self.username,
            "password": self.password,
            "is_main": self.is_main
        }
    
    @staticmethod
    def from_dict(data: dict):
        return Account(data["username"], data["password"], data.get("is_main", False))

class AccountManager:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self.load_config()
        self.accounts: List[Account] = []
        self.load_accounts()
    
    def load_config(self) -> Dict:
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {
            "max_accounts": 5,
            "game_url": "https://www.roblox.com/games/5233782396/Creatures-of-Sonaria-Survive-Kaiju-Animals",
            "game_name": "Creatures of Sonaria",
            "accounts": [],
            "theme": "dark",
            "macros_enabled": False  # Disabled by default to reduce AV false positives
        }
    
    def save_config(self):
        self.config["accounts"] = [acc.to_dict() for acc in self.accounts]
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def load_accounts(self):
        self.accounts = []
        for acc_data in self.config.get("accounts", []):
            self.accounts.append(Account.from_dict(acc_data))
    
    def add_account(self, username: str, password: str, is_main: bool = False) -> bool:
        if len(self.accounts) >= self.config["max_accounts"]:
            return False
        
        # Check if account already exists
        if any(acc.username == username for acc in self.accounts):
            return False
        
        # Only one main account allowed
        if is_main:
            for acc in self.accounts:
                acc.is_main = False
        
        self.accounts.append(Account(username, password, is_main))
        self.save_config()
        return True
    
    def remove_account(self, username: str) -> bool:
        self.accounts = [acc for acc in self.accounts if acc.username != username]
        self.save_config()
        return True
    
    def get_account(self, username: str) -> Account:
        for acc in self.accounts:
            if acc.username == username:
                return acc
        return None
    
    def get_main_account(self) -> Account:
        for acc in self.accounts:
            if acc.is_main:
                return acc
        return None
    
    def get_all_accounts(self) -> List[Account]:
        return self.accounts
    
    def update_account_status(self, username: str, status: str):
        acc = self.get_account(username)
        if acc:
            acc.status = status
