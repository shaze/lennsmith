#!/usr/bin/env python3
"""
Live Race Results Display System
Usage: python live_results.py <database_file.db>
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import sqlite3
import sys
import os
import time
import threading
from datetime import datetime


class LiveResultsDisplay:
    def __init__(self, db_path):
        self.db_path = db_path
        self.last_modified = 0
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("🏃‍♂️ Live Race Results 🏃‍♀️")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')
        
        # Create main frame with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="🏃‍♂️ LIVE RACE RESULTS 🏃‍♀️", 
                               font=('Arial', 18, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 15))
        
        # Left column
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        left_frame.columnconfigure(0, weight=1)
        
        # Right column
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))
        right_frame.columnconfigure(0, weight=1)
        
        # Create sections
        self.create_individual_sections(left_frame)
        self.create_team_and_stats_sections(right_frame)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Starting up...")
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        status_frame.columnconfigure(1, weight=1)
        
        ttk.Label(status_frame, text="Status:").grid(row=0, column=0, padx=(0, 5))
        status_label = ttk.Label(status_frame, textvariable=self.status_var, foreground='blue')
        status_label.grid(row=0, column=1, sticky=tk.W)
        
        # Last update time
        self.last_update_var = tk.StringVar()
        self.last_update_var.set("")
        ttk.Label(status_frame, textvariable=self.last_update_var, foreground='gray').grid(row=0, column=2)
        
        # Start monitoring
        self.check_for_updates()
    
    def create_individual_sections(self, parent):
        """Create sections for individual results"""
        row = 0
        
        # Top 6 Men
        ttk.Label(parent, text="🥇 TOP 10 MEN", font=('Arial', 12, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(5, 2))
        row += 1
        
        self.men_tree = ttk.Treeview(parent, columns=('pos', 'name', 'unit', 'time','reg'), 
                                     show='headings', height=10)
        self.men_tree.heading('pos', text='Pos')
        self.men_tree.heading('name', text='Name')
        self.men_tree.heading('unit', text='Organisation')
        self.men_tree.heading('time', text='Time')
        self.men_tree.heading('reg', text='Reg')        
        self.men_tree.column('pos', width=20)
        self.men_tree.column('name', width=150)
        self.men_tree.column('unit', width=150)
        self.men_tree.column('time', width=50)
        self.men_tree.column('reg', width=30)        
        self.men_tree.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        row += 1
        
        # Top 6 Women
        ttk.Label(parent, text="🥇 TOP 10 WOMEN", font=('Arial', 12, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(5, 2))
        row += 1
        
        self.women_tree = ttk.Treeview(parent, columns=('pos', 'name', 'unit', 'time','reg'), 
                                       show='headings', height=10)
        self.women_tree.heading('pos', text='Pos')
        self.women_tree.heading('name', text='Name')
        self.women_tree.heading('unit', text='Organisation')
        self.women_tree.heading('time', text='Time')
        self.women_tree.heading('reg', text='Reg')                
        self.women_tree.column('pos', width=20)
        self.women_tree.column('name', width=150)
        self.women_tree.column('unit', width=150)
        self.women_tree.column('time', width=50)
        self.women_tree.column('reg', width=30)                
        self.women_tree.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        row += 1
        
        # Latest 3 finishers
        ttk.Label(parent, text="🆕 LATEST 6 FINISHERS", font=('Arial', 12, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(5, 2))
        row += 1
        
        self.latest_tree = ttk.Treeview(parent, columns=('pos', 'name', 'unit', 'time','reg'), 
                                        show='headings', height=6)
        self.latest_tree.heading('pos', text='Pos')
        self.latest_tree.heading('name', text='Name')
        self.latest_tree.heading('unit', text='Organisation')
        self.latest_tree.heading('time', text='Time')
        self.latest_tree.heading('reg', text='Reg')                
        self.latest_tree.column('pos', width=20)
        self.latest_tree.column('name', width=150)
        self.latest_tree.column('unit', width=150)
        self.latest_tree.column('time', width=50)
        self.latest_tree.column('reg', width=30)                
        self.latest_tree.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
    
    def create_team_and_stats_sections(self, parent):
        """Create sections for team results and statistics"""
        row = 0
        
        # Top 2 Men's Teams
        ttk.Label(parent, text="🏆 TOP 2 MEN'S TEAMS", font=('Arial', 12, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(5, 2))
        row += 1
        
        self.men_teams_text = scrolledtext.ScrolledText(parent, height=20, width=50, 
                                                       font=('Courier', 11), wrap=tk.WORD)
        self.men_teams_text.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        row += 1
        
        # Top 2 Women's Teams
        ttk.Label(parent, text="🏆 TOP 2 WOMEN'S TEAMS", font=('Arial', 12, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(5, 2))
        row += 1
        
        self.women_teams_text = scrolledtext.ScrolledText(parent, height=20, width=50, 
                                                         font=('Courier', 11), wrap=tk.WORD)
        self.women_teams_text.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        row += 1
        
        # Statistics
        ttk.Label(parent, text="📊 STATISTICS", font=('Arial', 12, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(5, 2))
        row += 1
        
        self.stats_text = scrolledtext.ScrolledText(parent, height=6, width=50, 
                                                   font=('Arial', 10), wrap=tk.WORD)
        self.stats_text.grid(row=row, column=0, sticky=(tk.W, tk.E))
    
    def get_display_name(self, first_name, last_name, list_results):
        """Return name or 'Anonymous' based on list_results preference"""
        if list_results == 'not':
            return "Anonymous"
        return f"{first_name} {last_name}"
    
    def format_time(self, seconds):
        """Convert seconds to MM:SS format"""
        if seconds is None:
            return "DNF"
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def normalize_gender(self, gender):
        """Normalize gender values"""
        if not gender or gender.lower() == 'prefer-not-to-say':
            return 'other'
        return gender.lower()
    
    def get_top_individual_results(self, gender, limit=6):
        """Get top individual results for a specific gender"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT first_name, last_name, organisational_unit, elapsed, list_results, gender_pos, registration_number
            FROM registrations 
            WHERE gender = ? AND gender_pos IS NOT NULL
            ORDER BY gender_pos
            LIMIT ?
        """, (gender, limit))
        
        results = cursor.fetchall()
        conn.close()
        return results
    
    def get_latest_finishers(self, limit=6):
        """Get the latest finishers"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT first_name, last_name, organisational_unit, elapsed, list_results, position, registration_number
            FROM registrations 
            WHERE position IS NOT NULL
            ORDER BY position DESC
            LIMIT ?
        """, (limit,))
        
        results = cursor.fetchall()
        conn.close()
        return results
    
    def get_top_teams(self, gender, limit=2):
        """Get top teams for a specific gender"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get teams with at least 4 finishers
        cursor.execute("""
            SELECT organisational_unit,
                   SUM(elapsed) as total_time,
                   COUNT(*) as runner_count
            FROM (
                SELECT organisational_unit, elapsed,
                       ROW_NUMBER() OVER (PARTITION BY organisational_unit ORDER BY elapsed) as rn
                FROM registrations 
                WHERE gender = ? AND position IS NOT NULL
            ) ranked
            WHERE rn <= 4
            GROUP BY organisational_unit
            HAVING COUNT(*) = 4
            ORDER BY total_time
            LIMIT ?
        """, (gender, limit))
        
        teams = cursor.fetchall()
        
        # Get the runners for each team
        team_details = []
        for team in teams:
            cursor.execute("""
                SELECT first_name, last_name, elapsed, list_results
                FROM registrations 
                WHERE organisational_unit = ? AND gender = ? AND position IS NOT NULL
                ORDER BY elapsed
                LIMIT 4
            """, (team['organisational_unit'], gender))
            runners = cursor.fetchall()
            team_details.append((team['organisational_unit'], team['total_time'], runners))
        
        conn.close()
        return team_details
    
    def get_statistics(self):
        """Get race statistics"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Most finishers by organisational unit
        cursor.execute("""
            SELECT organisational_unit, COUNT(*) as count
            FROM registrations 
            WHERE position IS NOT NULL
            GROUP BY organisational_unit
            ORDER BY count DESC
            LIMIT 1
        """)
        top_org = cursor.fetchone()
        
        # Total finishers
        cursor.execute("SELECT COUNT(*) as total FROM registrations WHERE position IS NOT NULL")
        total_finishers = cursor.fetchone()['total']
        
        conn.close()
        
        return {
            'top_org': top_org,
            'total_finishers': total_finishers
        }
    
    def update_individual_results(self):
        """Update individual results display"""
        # Clear existing data
        for item in self.men_tree.get_children():
            self.men_tree.delete(item)
        for item in self.women_tree.get_children():
            self.women_tree.delete(item)
        for item in self.latest_tree.get_children():
            self.latest_tree.delete(item)
        
        # Update men's results
        men_results = self.get_top_individual_results('male', 10)
        for result in men_results:
            name = self.get_display_name(result['first_name'], result['last_name'], result['list_results'])
            self.men_tree.insert('', 'end', values=(
                result['gender_pos'],
                name,
                result['organisational_unit'],
                self.format_time(result['elapsed']),
                result['registration_number']
            ))
        
        # Update women's results
        women_results = self.get_top_individual_results('female', 10)
        for result in women_results:
            name = self.get_display_name(result['first_name'], result['last_name'], result['list_results'])
            self.women_tree.insert('', 'end', values=(
                result['gender_pos'],
                name,
                result['organisational_unit'],
                self.format_time(result['elapsed']),
                result['registration_number']
            ))
        
        # Update latest finishers
        latest_results = self.get_latest_finishers(6)
        for result in latest_results:
            name = self.get_display_name(result['first_name'], result['last_name'], result['list_results'])
            self.latest_tree.insert('', 'end', values=(
                result['position'],
                name,
                result['organisational_unit'],
                self.format_time(result['elapsed']),
                result['registration_number']
            ))
    
    def update_team_results(self):
        """Update team results display"""
        # Men's teams
        self.men_teams_text.delete(1.0, tk.END)
        men_teams = self.get_top_teams('male', 2)
        
        if not men_teams:
            self.men_teams_text.insert(tk.END, "No eligible teams yet\n(need 4 finishers per team)")
        else:
            for i, (org_unit, total_time, runners) in enumerate(men_teams, 1):
                team_time = self.format_time(total_time)
                self.men_teams_text.insert(tk.END, f"{i}. {org_unit}\n")
                self.men_teams_text.insert(tk.END, f"   Total Time: {team_time}\n")
                for j, runner in enumerate(runners, 1):
                    name = self.get_display_name(runner['first_name'], runner['last_name'], runner['list_results'])
                    time_str = self.format_time(runner['elapsed'])
                    self.men_teams_text.insert(tk.END, f"   {j}. {name:<20} {time_str}\n")
                self.men_teams_text.insert(tk.END, "\n")
        
        # Women's teams
        self.women_teams_text.delete(1.0, tk.END)
        women_teams = self.get_top_teams('female', 2)
        
        if not women_teams:
            self.women_teams_text.insert(tk.END, "No eligible teams yet\n(need 4 finishers per team)")
        else:
            for i, (org_unit, total_time, runners) in enumerate(women_teams, 1):
                team_time = self.format_time(total_time)
                self.women_teams_text.insert(tk.END, f"{i}. {org_unit}\n")
                self.women_teams_text.insert(tk.END, f"   Total Time: {team_time}\n")
                for j, runner in enumerate(runners, 1):
                    name = self.get_display_name(runner['first_name'], runner['last_name'], runner['list_results'])
                    time_str = self.format_time(runner['elapsed'])
                    self.women_teams_text.insert(tk.END, f"   {j}. {name:<20} {time_str}\n")
                self.women_teams_text.insert(tk.END, "\n")
    
    def update_statistics(self):
        """Update statistics display"""
        self.stats_text.delete(1.0, tk.END)
        stats = self.get_statistics()
        
        # Most participating unit
        if stats['top_org']:
            self.stats_text.insert(tk.END, f"Most finishers: {stats['top_org']['organisational_unit']}\n")
            self.stats_text.insert(tk.END, f"({stats['top_org']['count']} runners)\n\n")
        else:
            self.stats_text.insert(tk.END, "No finishers yet\n\n")
        
        # Total finishers
        self.stats_text.insert(tk.END, f"Total finishers: {stats['total_finishers']}\n")
        
        # Current time
        current_time = datetime.now().strftime("%H:%M:%S")
        self.stats_text.insert(tk.END, f"\nLast updated: {current_time}")
    
    def update_all_displays(self):
        """Update all display sections"""
        try:
            self.update_individual_results()
            self.update_team_results()
            self.update_statistics()
            
            self.status_var.set("Display updated successfully")
            self.last_update_var.set(f"Last update: {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            self.status_var.set(f"Error updating display: {str(e)}")
    
    def check_for_updates(self):
        """Check if database file has been modified and update display"""
        try:
            if os.path.exists(self.db_path):
                current_modified = os.path.getmtime(self.db_path)
                
                if current_modified != self.last_modified:
                    self.last_modified = current_modified
                    self.update_all_displays()
                elif self.last_modified == 0:
                    # First run
                    self.last_modified = current_modified
                    self.update_all_displays()
            else:
                self.status_var.set(f"Database file not found: {self.db_path}")
                
        except Exception as e:
            self.status_var.set(f"Error checking file: {str(e)}")
        
        # Schedule next check in 10 seconds
        self.root.after(5000, self.check_for_updates)
    
    def run(self):
        """Start the GUI"""
        self.root.mainloop()


def main():
    if len(sys.argv) != 2:
        print("Usage: python live_results.py <database_file.db>")
        sys.exit(1)
    
    db_path = sys.argv[1]
    
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        sys.exit(1)
    
    try:
        # Test database connection
        conn = sqlite3.connect(db_path)
        conn.close()
        
        # Start the display system
        display = LiveResultsDisplay(db_path)
        display.run()
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
