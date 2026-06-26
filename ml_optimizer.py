
import json
import os
import time
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import re


class AdaptiveRateLimiter:
    
    def __init__(self, config: Dict):
        self.config = config
        self.min_wait = config.get('min_wait_seconds', 2)
        self.max_wait = config.get('max_wait_seconds', 10)
        self.current_wait = 5
        
        self.success_rate = 1.0
        self.recent_successes = []
        self.recent_times = []
        self.learning_rate = 0.1
        
        self.history_file = 'ml_models/rate_history.pkl'
        self.load_history()
    
    def load_history(self):
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'rb') as f:
                    data = pickle.load(f)
                    self.current_wait = data.get('optimal_wait', self.current_wait)
                    self.recent_successes = data.get('recent_successes', [])[-50:]
                    print(f"[ML] Loaded historical rate data. Optimal wait: {self.current_wait:.1f}s")
        except Exception as e:
            print(f"[ML] Could not load history: {e}")
    
    def save_history(self):
        try:
            os.makedirs('ml_models', exist_ok=True)
            data = {
                'optimal_wait': self.current_wait,
                'recent_successes': self.recent_successes[-50:],
                'last_updated': datetime.now().isoformat()
            }
            with open(self.history_file, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            print(f"[ML] Could not save history: {e}")
    
    def get_wait_time(self, hour_of_day: int = None) -> float:
        if hour_of_day is None:
            hour_of_day = datetime.now().hour
        
        time_multiplier = 1.0
        if 9 <= hour_of_day <= 17:
            time_multiplier = 1.2
        elif 22 <= hour_of_day or hour_of_day <= 6:
            time_multiplier = 0.8
        
        if len(self.recent_successes) >= 5:
            recent_success_rate = sum(self.recent_successes[-10:]) / len(self.recent_successes[-10:])
            
            if recent_success_rate > 0.95:
                self.current_wait = max(self.min_wait, self.current_wait * 0.95)
            elif recent_success_rate < 0.8:
                self.current_wait = min(self.max_wait, self.current_wait * 1.3)
        
        wait_time = self.current_wait * time_multiplier
        return max(self.min_wait, min(self.max_wait, wait_time))
    
    def record_attempt(self, success: bool, response_time: float = None):
        self.recent_successes.append(1 if success else 0)
        if response_time:
            self.recent_times.append(response_time)
        
        if len(self.recent_successes) > 50:
            self.recent_successes = self.recent_successes[-50:]
        if len(self.recent_times) > 50:
            self.recent_times = self.recent_times[-50:]
        
        if len(self.recent_successes) % 10 == 0:
            self.save_history()
    
    def get_stats(self) -> Dict:
        if self.recent_successes:
            success_rate = sum(self.recent_successes) / len(self.recent_successes)
        else:
            success_rate = 1.0
        
        avg_response_time = np.mean(self.recent_times) if self.recent_times else 0
        
        return {
            'current_wait': self.current_wait,
            'success_rate': success_rate,
            'avg_response_time': avg_response_time,
            'total_attempts': len(self.recent_successes)
        }


class ActionSpeedOptimizer:
    
    def __init__(self, config: Dict):
        self.config = config
        self.enabled = config.get('enable_dynamic_action_delays', False)
        self.target_time = config.get('target_send_time_seconds', 35.0)
        self.min_multiplier = 0.3  # Don't go faster than 30% of base delay
        self.current_multiplier = 1.0
        
        self.history_file = 'ml_models/speed_history.pkl'
        self.recent_times = []
        self.recent_successes = []
        self.load_history()
        
    def load_history(self):
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'rb') as f:
                    data = pickle.load(f)
                    self.current_multiplier = data.get('multiplier', self.current_multiplier)
                    self.recent_times = data.get('recent_times', [])[-20:]
                    self.recent_successes = data.get('recent_successes', [])[-20:]
                    print(f"[ML] Loaded historical speed data. Action multiplier: {self.current_multiplier:.2f}x")
        except Exception as e:
            pass
            
    def save_history(self):
        try:
            os.makedirs('ml_models', exist_ok=True)
            data = {
                'multiplier': self.current_multiplier,
                'recent_times': self.recent_times[-20:],
                'recent_successes': self.recent_successes[-20:]
            }
            with open(self.history_file, 'wb') as f:
                pickle.dump(data, f)
        except Exception:
            pass
            
    def record_attempt(self, success: bool, time_taken: float = None):
        if not self.enabled:
            return
            
        self.recent_successes.append(1 if success else 0)
        if time_taken is not None:
            self.recent_times.append(time_taken)
            
        if len(self.recent_successes) > 20:
            self.recent_successes = self.recent_successes[-20:]
        if len(self.recent_times) > 20:
            self.recent_times = self.recent_times[-20:]
            
        # Recalculate multiplier every 3 attempts
        if len(self.recent_successes) % 3 == 0:
            self.optimize_multiplier()
            self.save_history()
            
    def optimize_multiplier(self):
        if not self.recent_times or not self.recent_successes:
            return
            
        avg_success = sum(self.recent_successes) / len(self.recent_successes)
        avg_time = sum(self.recent_times) / len(self.recent_times)
        
        if avg_success >= 0.9:  # Reliable, feel free to speed up if slow
            if avg_time > self.target_time * 1.05:
                # We are too slow, increase speed (decrease multiplier)
                self.current_multiplier = max(self.min_multiplier, self.current_multiplier * 0.9)
                print(f"⚡ [ML] Speeding up UI actions. new multiplier: {self.current_multiplier:.2f}x (avg time: {avg_time:.1f}s)")
            elif avg_time < self.target_time * 0.9:
                pass # Already faster, leave it
        elif avg_success < 0.7:  # Failing too much, slow down
            self.current_multiplier = min(1.0, self.current_multiplier * 1.2)
            print(f"🐢 [ML] Slowing down UI actions to improve stability. new multiplier: {self.current_multiplier:.2f}x")
            
    def get_action_delay(self, base_delay: float) -> float:
        if not self.enabled:
            return base_delay
        # Calculate scaled delay but maintain a minimum absolute delay
        return max(0.1, base_delay * self.current_multiplier)


class ContactPrioritizer:
    
    def __init__(self):
        self.domain_scores = {}
        self.load_domain_knowledge()
    
    def load_domain_knowledge(self):
        high_priority_domains = ['gmail.com', 'outlook.com', 'yahoo.com', 'company.com']
        for domain in high_priority_domains:
            self.domain_scores[domain] = 0.8
    
    def score_contact(self, email: str, name: str) -> float:
        score = 0.5
        
        try:
            domain = email.split('@')[1].lower() if '@' in email else ''
            
            if domain in self.domain_scores:
                score += self.domain_scores[domain] * 0.3
            elif domain.endswith('.edu'):
                score += 0.2
            elif domain.endswith('.gov'):
                score += 0.3
            elif not domain.endswith(('.gmail.com', '.yahoo.com', '.outlook.com')):
                score += 0.25
            
            if name and len(name.split()) >= 2:
                score += 0.1
            
            if email and re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                score += 0.1
            
        except Exception as e:
            pass
        
        return min(1.0, max(0.0, score))
    
    def prioritize_contacts(self, contacts_df: pd.DataFrame) -> pd.DataFrame:
        contacts_df = contacts_df.copy()
        
        contacts_df['priority_score'] = contacts_df.apply(
            lambda row: self.score_contact(
                row.get('Email', ''), 
                row.get('Name', '')
            ),
            axis=1
        )
        
        contacts_df = contacts_df.sort_values('priority_score', ascending=False)
        
        return contacts_df


class EngagementPredictor:
    
    def __init__(self):
        self.feature_weights = {
            'has_business_email': 0.3,
            'name_formality': 0.2,
            'time_of_day': 0.2,
            'domain_reputation': 0.3
        }
    
    def predict_engagement(self, email: str, name: str, send_time: datetime = None) -> float:
        if send_time is None:
            send_time = datetime.now()
        
        score = 0.5
        
        domain = email.split('@')[1] if '@' in email else ''
        if not domain.endswith(('.gmail.com', '.yahoo.com', '.outlook.com', '.hotmail.com')):
            score += self.feature_weights['has_business_email']
        
        if name and len(name.split()) >= 2:
            score += self.feature_weights['name_formality']
        
        hour = send_time.hour
        if 9 <= hour <= 17:
            score += self.feature_weights['time_of_day']
        elif 8 <= hour <= 18:
            score += self.feature_weights['time_of_day'] * 0.5
        
        return min(1.0, max(0.0, score))
    
    def get_best_send_time(self, base_time: datetime = None) -> datetime:
        if base_time is None:
            base_time = datetime.now()
        
        hour = base_time.hour
        
        if hour < 8:
            next_send = base_time.replace(hour=9, minute=0)
        elif hour >= 18:
            next_send = base_time + timedelta(days=1)
            next_send = next_send.replace(hour=9, minute=0)
        else:
            next_send = base_time
        
        return next_send


class MLOptimizer:
    
    def __init__(self, config_path: str = 'config.json'):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.rate_limiter = AdaptiveRateLimiter(self.config)
        self.contact_prioritizer = ContactPrioritizer()
        self.engagement_predictor = EngagementPredictor()
        self.action_speed = ActionSpeedOptimizer(self.config)
        
        self.session_stats = {
            'total_sent': 0,
            'total_success': 0,
            'total_failed': 0,
            'start_time': datetime.now(),
            'avg_time_per_email': 0
        }
        
        print("[ML] Optimizer initialized with adaptive learning enabled")
    
    def optimize_contact_list(self, contacts_df: pd.DataFrame) -> pd.DataFrame:
        if self.config.get('enable_contact_prioritization', True):
            print("[ML] Prioritizing contacts using ML scoring...")
            contacts_df = self.contact_prioritizer.prioritize_contacts(contacts_df)
            print(f"[ML] Contacts sorted by engagement probability")
        
        return contacts_df
    
    def get_optimal_wait_time(self) -> float:
        return self.rate_limiter.get_wait_time()
        
    def get_action_delay(self, base_delay: float) -> float:
        """Get the ML-optimized delay duration for UI actions"""
        return self.action_speed.get_action_delay(base_delay)
    
    def record_send_attempt(self, success: bool, time_taken: float = None):
        self.rate_limiter.record_attempt(success, time_taken)
        self.action_speed.record_attempt(success, time_taken)
        
        if success:
            self.session_stats['total_success'] += 1
        else:
            self.session_stats['total_failed'] += 1
        
        self.session_stats['total_sent'] += 1
    
    def get_engagement_prediction(self, email: str, name: str) -> Dict:
        if not self.config.get('enable_engagement_prediction', True):
            return {'probability': 0.5, 'confidence': 'low'}
        
        probability = self.engagement_predictor.predict_engagement(email, name)
        
        return {
            'probability': probability,
            'confidence': 'high' if probability > 0.7 else 'medium' if probability > 0.5 else 'low',
            'recommendation': 'high_priority' if probability > 0.7 else 'normal'
        }
    
    def get_session_stats(self) -> Dict:
        elapsed = (datetime.now() - self.session_stats['start_time']).total_seconds()
        
        stats = self.session_stats.copy()
        stats['elapsed_time'] = elapsed
        stats['success_rate'] = (self.session_stats['total_success'] / 
                                self.session_stats['total_sent']) if self.session_stats['total_sent'] > 0 else 0
        stats['emails_per_minute'] = (self.session_stats['total_sent'] / 
                                     (elapsed / 60)) if elapsed > 0 else 0
        stats['rate_limiter_stats'] = self.rate_limiter.get_stats()
        
        return stats
    
    def print_performance_summary(self):
        stats = self.get_session_stats()
        
        print("\n" + "="*60)
        print("   ML OPTIMIZER PERFORMANCE SUMMARY")
        print("="*60)
        print(f"Total Sent: {stats['total_sent']}")
        print(f"Success: {stats['total_success']} | Failed: {stats['total_failed']}")
        print(f"Success Rate: {stats['success_rate']*100:.1f}%")
        print(f"Speed: {stats['emails_per_minute']:.1f} emails/minute")
        print(f"Elapsed Time: {stats['elapsed_time']/60:.1f} minutes")
        print(f"\nML Rate Limiter:")
        print(f"  Current Wait Time: {stats['rate_limiter_stats']['current_wait']:.1f}s")
        print(f"  Avg Response Time: {stats['rate_limiter_stats']['avg_response_time']:.2f}s")
        print(f"  Action Speed Multiplier: {self.action_speed.current_multiplier:.2f}x")
        print("="*60)


_optimizer_instance = None

def get_optimizer(config_path: str = 'config.json') -> MLOptimizer:
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = MLOptimizer(config_path)
    return _optimizer_instance
