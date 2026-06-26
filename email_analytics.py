
import json
import os
from datetime import datetime
from typing import Dict, List
import pandas as pd


class EmailAnalytics:
    
    def __init__(self):
        self.analytics_file = 'ml_models/analytics.json'
        self.history_file = 'ml_models/sending_history.csv'
        
        os.makedirs('ml_models', exist_ok=True)
        
        self.session_data = []
        self.load_history()
    
    def load_history(self):
        try:
            if os.path.exists(self.history_file):
                self.history_df = pd.read_csv(self.history_file)
                print(f"[Analytics] Loaded {len(self.history_df)} historical records")
            else:
                self.history_df = pd.DataFrame()
        except Exception as e:
            print(f"[Analytics] Could not load history: {e}")
            self.history_df = pd.DataFrame()
    
    def record_send(self, contact_data: Dict):
        record = {
            'timestamp': datetime.now().isoformat(),
            'name': contact_data.get('name', ''),
            'email': contact_data.get('email', ''),
            'success': contact_data.get('success', False),
            'time_taken': contact_data.get('time_taken', 0),
            'wait_time': contact_data.get('wait_time', 0),
            'priority_score': contact_data.get('priority_score', 0),
            'engagement_prediction': contact_data.get('engagement_prediction', 0),
            'error': contact_data.get('error', '')
        }
        
        self.session_data.append(record)
        
        if len(self.session_data) % 5 == 0:
            self.save_session()
    
    def save_session(self):
        try:
            if self.session_data:
                df = pd.DataFrame(self.session_data)
                
                if os.path.exists(self.history_file):
                    df.to_csv(self.history_file, mode='a', header=False, index=False)
                else:
                    df.to_csv(self.history_file, index=False)
                
                print(f"[Analytics] Saved {len(self.session_data)} records")
        except Exception as e:
            print(f"[Analytics] Error saving: {e}")
    
    def get_realtime_stats(self) -> Dict:
        if not self.session_data:
            return {
                'total_sent': 0,
                'success_rate': 0,
                'avg_time': 0,
                'emails_per_minute': 0,
                'total_time_saved': 0
            }
        
        df = pd.DataFrame(self.session_data)
        
        total = len(df)
        successes = df['success'].sum()
        avg_time = df['time_taken'].mean()
        
        if total > 1:
            start = pd.to_datetime(df['timestamp'].iloc[0])
            end = pd.to_datetime(df['timestamp'].iloc[-1])
            duration_minutes = (end - start).total_seconds() / 60
            emails_per_minute = total / duration_minutes if duration_minutes > 0 else 0
        else:
            emails_per_minute = 0
        
        return {
            'total_sent': total,
            'success_rate': successes / total if total > 0 else 0,
            'avg_time': avg_time,
            'emails_per_minute': emails_per_minute,
            'total_time_saved': self._calculate_time_saved()
        }
    
    def _calculate_time_saved(self) -> float:
        if not self.session_data:
            return 0
        
        df = pd.DataFrame(self.session_data)
        actual_time = df['time_taken'].sum() + df['wait_time'].sum()
        old_system_time = len(df) * 60
        
        return old_system_time - actual_time
    
    def print_dashboard(self):
        stats = self.get_realtime_stats()
        
        try:
            print("\n" + "┌" + "─"*58 + "┐")
            print("│" + " "*15 + "📊 REAL-TIME ANALYTICS" + " "*20 + "│")
            print("├" + "─"*58 + "┤")
            print(f"│ Total Sent:        {stats['total_sent']:<39} │")
            print(f"│ Success Rate:      {stats['success_rate']*100:>5.1f}%" + " "*32 + "│")
            print(f"│ Avg Time/Email:    {stats['avg_time']:>5.1f}s" + " "*31 + "│")
            print(f"│ Speed:             {stats['emails_per_minute']:>5.1f} emails/min" + " "*21 + "│")
            
            if stats['total_time_saved'] > 0:
                minutes_saved = stats['total_time_saved'] / 60
                print(f"│ ⚡ Time Saved:      {minutes_saved:>5.1f} minutes" + " "*23 + "│")
            
            print("└" + "─"*58 + "┘\n")
        except UnicodeEncodeError:
            print("\n" + "+" + "-"*58 + "+")
            print("|" + " "*15 + "REAL-TIME ANALYTICS" + " "*24 + "|")
            print("+" + "-"*58 + "+")
            print(f"| Total Sent:        {stats['total_sent']:<39} |")
            print(f"| Success Rate:      {stats['success_rate']*100:>5.1f}%" + " "*32 + "|")
            print(f"| Avg Time/Email:    {stats['avg_time']:>5.1f}s" + " "*31 + "|")
            print(f"| Speed:             {stats['emails_per_minute']:>5.1f} emails/min" + " "*21 + "|")
            
            if stats['total_time_saved'] > 0:
                minutes_saved = stats['total_time_saved'] / 60
                print(f"| Time Saved:        {minutes_saved:>5.1f} minutes" + " "*23 + "|")
            
            print("+" + "-"*58 + "+\n")
    
    def generate_report(self, filename: str = 'performance_report.txt'):
        stats = self.get_realtime_stats()
        
        report = f"""
EMAIL SENDING PERFORMANCE REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}

SUMMARY STATISTICS
------------------
Total Emails Sent:     {stats['total_sent']}
Successful:            {int(stats['total_sent'] * stats['success_rate'])}
Failed:                {int(stats['total_sent'] * (1 - stats['success_rate']))}
Success Rate:          {stats['success_rate']*100:.1f}%

PERFORMANCE METRICS
-------------------
Average Time/Email:    {stats['avg_time']:.1f} seconds
Sending Speed:         {stats['emails_per_minute']:.1f} emails/minute
Time Saved (vs 60s):   {stats['total_time_saved']/60:.1f} minutes

EFFICIENCY COMPARISON
---------------------
Old System:            1 email/minute (60s wait)
New System:            {stats['emails_per_minute']:.1f} emails/minute
Speed Improvement:     {stats['emails_per_minute']:.1f}x faster

{'='*60}
        """
        
        try:
            with open(filename, 'w') as f:
                f.write(report)
            print(f"[Analytics] Report saved to {filename}")
        except Exception as e:
            print(f"[Analytics] Could not save report: {e}")
        
        return report
    
    def get_top_performers(self, n: int = 10) -> pd.DataFrame:
        if not self.session_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.session_data)
        top = df.nlargest(n, 'engagement_prediction')[['name', 'email', 'engagement_prediction', 'success']]
        
        return top


_analytics_instance = None

def get_analytics() -> EmailAnalytics:
    global _analytics_instance
    if _analytics_instance is None:
        _analytics_instance = EmailAnalytics()
    return _analytics_instance
