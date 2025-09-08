#!/usr/bin/env python3
"""
Race Results Capture System
Usage: python race_results.py <database_file.db>
"""

import sqlite3
import sys
import time
import re
from collections import defaultdict
from datetime import datetime


class RaceResultsCapture:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.start_time = None
        self.current_position = 1
        self.gender_positions = {'male': 1, 'female': 1, 'other': 1}
        self.initialize_database()
    
    def initialize_database(self):
        """Check if race has started and get current state"""
        # Get start time
        self.cursor.execute("SELECT start FROM start_time LIMIT 1")
        result = self.cursor.fetchone()
        if result and result['start']:
            self.start_time = result['start']
            print(f"Race already started at {datetime.fromtimestamp(self.start_time)}")
            
            # Get current position counters
            self.cursor.execute("SELECT MAX(position) as max_pos FROM registrations WHERE position IS NOT NULL")
            result = self.cursor.fetchone()
            if result and result['max_pos']:
                self.current_position = result['max_pos'] + 1
            
            # Get gender position counters
            for gender in ['male', 'female']:
                self.cursor.execute("SELECT MAX(gender_pos) as max_pos FROM registrations WHERE gender = ? AND gender_pos IS NOT NULL", (gender,))
                result = self.cursor.fetchone()
                if result and result['max_pos']:
                    self.gender_positions[gender] = result['max_pos'] + 1
            
            # Get other gender position counter
            self.cursor.execute("SELECT MAX(gender_pos) as max_pos FROM registrations WHERE (gender IS NULL OR gender = 'prefer-not-to-say') AND gender_pos IS NOT NULL")
            result = self.cursor.fetchone()
            if result and result['max_pos']:
                self.gender_positions['other'] = result['max_pos'] + 1
        else:
            print("Race not started. Type 'start' to begin the race.")
    
    def start_race(self):
        """Record race start time"""
        self.start_time = int(time.time())
        
        # Create start_time table if it doesn't exist and insert start time
        self.cursor.execute("DELETE FROM start_time")  # Clear any existing entries
        self.cursor.execute("INSERT INTO start_time (start) VALUES (?)", (self.start_time,))
        self.conn.commit()
        
        print(f"Race started at {datetime.fromtimestamp(self.start_time)}")
        print("Enter runner IDs as they finish...")
    
    def normalize_gender(self, gender):
        """Normalize gender values"""
        if not gender or gender.lower() == 'prefer-not-to-say':
            return 'other'
        return gender.lower()
    
    def find_runner(self, input_id):
        """Find runner by registration number or staff_student_number"""
        # Check if it's a registration number (integer + optional letters)
        match = re.match(r'^(\d{1,3})\s*[a-zA-Z]*$', input_id.strip())
        if match:
            reg_num = match.group(1)
            # Try exact match first, then partial match
            self.cursor.execute("SELECT * FROM registrations WHERE registration_number = ?", (input_id.strip(),))
            runner = self.cursor.fetchone()
            if not runner:
                self.cursor.execute("SELECT * FROM registrations WHERE registration_number LIKE ?", (reg_num + '%',))
                runner = self.cursor.fetchone()
        else:
            # It's a staff_student_number
            self.cursor.execute("SELECT * FROM registrations WHERE staff_student_number = ?", (input_id.strip(),))
            runner = self.cursor.fetchone()
        
        return runner
    
    def record_finish(self, runner_id):
        """Record a runner's finish time"""
        if not self.start_time:
            print("Race hasn't started yet. Type 'start' first.")
            return False
        
        runner = self.find_runner(runner_id)
        if not runner:
            print(f"Runner not found: {runner_id}")
            return False
        
        # Check if runner already finished
        if runner['elapsed']:
            print(f"Runner {runner['first_name']} {runner['last_name']} already finished!")
            return False
        
        # Calculate elapsed time
        current_time = int(time.time())
        elapsed = current_time - self.start_time
        
        # Determine gender for position calculation
        gender = self.normalize_gender(runner['gender'])
        
        # Update runner record
        self.cursor.execute("""
            UPDATE registrations 
            SET elapsed = ?, position = ?, gender_pos = ?
            WHERE id = ?
        """, (elapsed, self.current_position, self.gender_positions[gender], runner['id']))
        
        self.conn.commit()
        
        # Display finish info
        minutes, seconds = divmod(elapsed, 60)
        print(f"Position {self.current_position}: {runner['first_name']} {runner['last_name']} - {minutes:02d}:{seconds:02d} (Gender pos: {self.gender_positions[gender]})")
        
        # Update counters
        self.current_position += 1
        self.gender_positions[gender] += 1
        
        return True
    
    def calculate_team_results(self):
        """Calculate team results for men and women"""
        teams = {'male': defaultdict(list), 'female': defaultdict(list)}
        
        # Get all finished runners
        self.cursor.execute("""
            SELECT first_name, last_name, organisational_unit, gender, elapsed, position
            FROM registrations 
            WHERE elapsed IS NOT NULL
            ORDER BY elapsed ASC
        """)
        
        for runner in self.cursor.fetchall():
            gender = self.normalize_gender(runner['gender'])
            if gender in ['male', 'female']:
                teams[gender][runner['organisational_unit']].append({
                    'name': f"{runner['first_name']} {runner['last_name']}",
                    'elapsed': runner['elapsed'],
                    'position': runner['position']
                })
        
        # Calculate team times (fastest 4 runners)
        team_results = {'male': [], 'female': []}
        
        for gender in ['male', 'female']:
            for unit, runners in teams[gender].items():
                if len(runners) >= 4:  # Must have at least 4 runners
                    # Sort by elapsed time and take fastest 4
                    runners.sort(key=lambda x: x['elapsed'])
                    top_4 = runners[:4]
                    total_time = sum(r['elapsed'] for r in top_4)
                    
                    team_results[gender].append({
                        'unit': unit,
                        'total_time': total_time,
                        'runners': top_4
                    })
            
            # Sort teams by total time
            team_results[gender].sort(key=lambda x: x['total_time'])
        
        return team_results
    
    def format_time(self, seconds):
        """Format elapsed time as MM:SS"""
        minutes, secs = divmod(seconds, 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def get_display_name_html(self, first_name, last_name, list_results):
        """Return name or 'Anonymous' based on list_results preference for HTML output"""
        if list_results == 'no':
            return "Anonymous"
        return f"{first_name} {last_name}"
    
    def generate_results_html(self):
        """Generate HTML results file"""
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lenn Smith Race 2025 - Results</title>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background-color: #f5f5f5; 
            color: #333;
        }
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
            background: white; 
            padding: 30px; 
            border-radius: 10px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 { 
            color: #2c3e50; 
            text-align: center; 
            margin-bottom: 30px; 
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }
        h2 { 
            color: #34495e; 
            border-bottom: 3px solid #3498db; 
            padding-bottom: 10px; 
            margin-top: 40px; 
            margin-bottom: 20px;
        }
        h3 { 
            color: #2980b9; 
            margin-top: 25px; 
            margin-bottom: 15px;
        }
        table { 
            border-collapse: collapse; 
            width: 100%; 
            margin: 20px 0; 
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        th, td { 
            border: 1px solid #ddd; 
            padding: 12px 15px; 
            text-align: left; 
        }
        th { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        tr:nth-child(even) { 
            background-color: #f8f9fa; 
        }
        tr:hover { 
            background-color: #e3f2fd; 
            transition: background-color 0.3s;
        }
        .section { 
            margin: 40px 0; 
            padding: 20px;
            border-radius: 8px;
        }
        .stats { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            padding: 20px; 
            border-radius: 10px; 
            margin: 20px 0;
            text-align: center;
        }
        .stats h3 { 
            color: white; 
            margin-top: 0;
        }
        .team-section {
            background-color: #f8f9fa;
            border-left: 5px solid #3498db;
            padding: 15px;
            margin: 20px 0;
        }
        .endurance-winner {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            margin: 20px 0;
            font-size: 1.2em;
        }
        .endurance-winner h3 {
            color: white;
            margin-top: 0;
        }
        .medal { font-size: 1.5em; }
        .gold { color: #FFD700; }
        .silver { color: #C0C0C0; }
        .bronze { color: #CD7F32; }
        .timestamp {
            text-align: center;
            color: #7f8c8d;
            margin-top: 30px;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏃‍♂️ Lenn Smith Race 2025 🏃‍♀️</h1>
        <div class="timestamp">Results generated on """ + datetime.now().strftime("%B %d, %Y at %H:%M:%S") + """</div>
"""
        
        # Top 6 Men
        html += '''
        <div class="section">
            <h2>🥇 Top 6 Men</h2>
            <table>
                <tr>
                    <th>Position</th>
                    <th>Name</th>
                    <th>Organisation</th>
                    <th>Time</th>
                </tr>'''
        
        self.cursor.execute("""
            SELECT first_name, last_name, organisational_unit, elapsed, list_results, gender_pos
            FROM registrations 
            WHERE gender = 'male' AND gender_pos IS NOT NULL
            ORDER BY gender_pos LIMIT 6
        """)
        
        for i, row in enumerate(self.cursor.fetchall(), 1):
            name = self.get_display_name_html(row['first_name'], row['last_name'], row['list_results'])
            medal = ""
            if i == 1: medal = '<span class="medal gold">🥇</span> '
            elif i == 2: medal = '<span class="medal silver">🥈</span> '
            elif i == 3: medal = '<span class="medal bronze">🥉</span> '
            
            html += f'''
                <tr>
                    <td>{medal}{row['gender_pos']}</td>
                    <td>{name}</td>
                    <td>{row['organisational_unit']}</td>
                    <td>{self.format_time(row['elapsed'])}</td>
                </tr>'''
        
        html += '''
            </table>
        </div>'''
        
        # Top 6 Women
        html += '''
        <div class="section">
            <h2>🥇 Top 6 Women</h2>
            <table>
                <tr>
                    <th>Position</th>
                    <th>Name</th>
                    <th>Organisation</th>
                    <th>Time</th>
                </tr>'''
        
        self.cursor.execute("""
            SELECT first_name, last_name, organisational_unit, elapsed, list_results, gender_pos
            FROM registrations 
            WHERE gender = 'female' AND gender_pos IS NOT NULL
            ORDER BY gender_pos LIMIT 6
        """)
        
        for i, row in enumerate(self.cursor.fetchall(), 1):
            name = self.get_display_name_html(row['first_name'], row['last_name'], row['list_results'])
            medal = ""
            if i == 1: medal = '<span class="medal gold">🥇</span> '
            elif i == 2: medal = '<span class="medal silver">🥈</span> '
            elif i == 3: medal = '<span class="medal bronze">🥉</span> '
            
            html += f'''
                <tr>
                    <td>{medal}{row['gender_pos']}</td>
                    <td>{name}</td>
                    <td>{row['organisational_unit']}</td>
                    <td>{self.format_time(row['elapsed'])}</td>
                </tr>'''
        
        html += '''
            </table>
        </div>'''
        
        # Top 2 Men's Teams
        html += '''
        <div class="section">
            <h2>🏆 Top 2 Men's Teams</h2>'''
        
        # Get men's teams
        self.cursor.execute("""
            SELECT organisational_unit, SUM(elapsed) as total_time
            FROM (
                SELECT organisational_unit, elapsed,
                       ROW_NUMBER() OVER (PARTITION BY organisational_unit ORDER BY elapsed) as rn
                FROM registrations 
                WHERE gender = 'male' AND position IS NOT NULL
            ) ranked
            WHERE rn <= 4
            GROUP BY organisational_unit
            HAVING COUNT(*) = 4
            ORDER BY total_time LIMIT 2
        """)
        
        men_teams = self.cursor.fetchall()
        if men_teams:
            for i, team in enumerate(men_teams, 1):
                medal = "🥇" if i == 1 else "🥈"
                html += f'''
                <div class="team-section">
                    <h3>{medal} {i}. {team['organisational_unit']} - Total Time: {self.format_time(team['total_time'])}</h3>
                    <table>
                        <tr><th>Runner</th><th>Time</th></tr>'''
                
                # Get team members
                self.cursor.execute("""
                    SELECT first_name, last_name, elapsed, list_results
                    FROM registrations 
                    WHERE organisational_unit = ? AND gender = 'male' AND position IS NOT NULL
                    ORDER BY elapsed LIMIT 4
                """, (team['organisational_unit'],))
                
                for runner in self.cursor.fetchall():
                    name = self.get_display_name_html(runner['first_name'], runner['last_name'], runner['list_results'])
                    html += f'''
                        <tr>
                            <td>{name}</td>
                            <td>{self.format_time(runner['elapsed'])}</td>
                        </tr>'''
                
                html += '''
                    </table>
                </div>'''
        else:
            html += '<p>No eligible men\'s teams (minimum 4 finishers required)</p>'
        
        html += '</div>'
        
        # Top 2 Women's Teams
        html += '''
        <div class="section">
            <h2>🏆 Top 2 Women's Teams</h2>'''
        
        # Get women's teams
        self.cursor.execute("""
            SELECT organisational_unit, SUM(elapsed) as total_time
            FROM (
                SELECT organisational_unit, elapsed,
                       ROW_NUMBER() OVER (PARTITION BY organisational_unit ORDER BY elapsed) as rn
                FROM registrations 
                WHERE gender = 'female' AND position IS NOT NULL
            ) ranked
            WHERE rn <= 4
            GROUP BY organisational_unit
            HAVING COUNT(*) = 4
            ORDER BY total_time LIMIT 2
        """)
        
        women_teams = self.cursor.fetchall()
        if women_teams:
            for i, team in enumerate(women_teams, 1):
                medal = "🥇" if i == 1 else "🥈"
                html += f'''
                <div class="team-section">
                    <h3>{medal} {i}. {team['organisational_unit']} - Total Time: {self.format_time(team['total_time'])}</h3>
                    <table>
                        <tr><th>Runner</th><th>Time</th></tr>'''
                
                # Get team members
                self.cursor.execute("""
                    SELECT first_name, last_name, elapsed, list_results
                    FROM registrations 
                    WHERE organisational_unit = ? AND gender = 'female' AND position IS NOT NULL
                    ORDER BY elapsed LIMIT 4
                """, (team['organisational_unit'],))
                
                for runner in self.cursor.fetchall():
                    name = self.get_display_name_html(runner['first_name'], runner['last_name'], runner['list_results'])
                    html += f'''
                        <tr>
                            <td>{name}</td>
                            <td>{self.format_time(runner['elapsed'])}</td>
                        </tr>'''
                
                html += '''
                    </table>
                </div>'''
        else:
            html += '<p>No eligible women\'s teams (minimum 4 finishers required)</p>'
        
        html += '</div>'
        
        # Statistics
        html += '''
        <div class="stats">
            <h3>📊 Race Statistics</h3>'''
        
        # Most participating organisation
        self.cursor.execute("""
            SELECT organisational_unit, COUNT(*) as count
            FROM registrations 
            WHERE position IS NOT NULL
            GROUP BY organisational_unit
            ORDER BY count DESC LIMIT 1
        """)
        top_org = self.cursor.fetchone()
        if top_org:
            html += f'<p><strong>Most Finishers:</strong> {top_org["organisational_unit"]} ({top_org["count"]} runners)</p>'
        
        # Total finishers
        self.cursor.execute("SELECT COUNT(*) as total FROM registrations WHERE position IS NOT NULL")
        total = self.cursor.fetchone()['total']
        html += f'<p><strong>Total Finishers:</strong> {total}</p>'
        
        html += '</div>'
        
        # Endurance Winner (last finisher)
        self.cursor.execute("""
            SELECT first_name, last_name, organisational_unit, elapsed, list_results
            FROM registrations 
            WHERE position IS NOT NULL
            ORDER BY position DESC LIMIT 1
        """)
        endurance_winner = self.cursor.fetchone()
        if endurance_winner:
            name = self.get_display_name_html(endurance_winner['first_name'], endurance_winner['last_name'], endurance_winner['list_results'])
            html += f'''
            <div class="endurance-winner">
                <h3>💪 Endurance Winner</h3>
                <p><strong>{name}</strong></p>
                <p>{endurance_winner['organisational_unit']}</p>
                <p>Time: {self.format_time(endurance_winner['elapsed'])}</p>
            </div>'''
        
        # Complete Results List
        html += '''
        <div class="section">
            <h2>📋 Complete Results</h2>
            <table>
                <tr>
                    <th>Overall Position</th>
                    <th>Name</th>
                    <th>Organisation</th>
                    <th>Time</th>
                </tr>'''
        
        self.cursor.execute("""
            SELECT first_name, last_name, organisational_unit, elapsed, list_results, position
            FROM registrations 
            WHERE position IS NOT NULL
            ORDER BY position
        """)
        
        for row in self.cursor.fetchall():
            name = self.get_display_name_html(row['first_name'], row['last_name'], row['list_results'])
            html += f'''
                <tr>
                    <td>{row['position']}</td>
                    <td>{name}</td>
                    <td>{row['organisational_unit']}</td>
                    <td>{self.format_time(row['elapsed'])}</td>
                </tr>'''
        
        html += '''
            </table>
        </div>
    </div>
</body>
</html>'''
        
        # Write HTML file
        with open('results.html', 'w', encoding='utf-8') as f:
            f.write(html)
        
        print("\n" + "="*50)
        print("🏁 RACE COMPLETE! 🏁")
        print("="*50)
        print(f"Results saved to results.html")
        print(f"Total finishers: {total}")
        print("="*50)
    
    def generate_results(self):
        """Generate both text and HTML results"""
        results = []
        
        # Top 5 men
        results.append("=== TOP 5 MEN ===")
        self.cursor.execute("""
            SELECT first_name, last_name, elapsed, position
            FROM registrations 
            WHERE (gender = 'male' OR gender = 'Male') AND elapsed IS NOT NULL
            ORDER BY gender_pos ASC
            LIMIT 5
        """)
        for i, runner in enumerate(self.cursor.fetchall(), 1):
            results.append(f"{i}. {runner['first_name']} {runner['last_name']} - {self.format_time(runner['elapsed'])}")
        
        results.append("")
        
        # Top 5 women
        results.append("=== TOP 5 WOMEN ===")
        self.cursor.execute("""
            SELECT first_name, last_name, elapsed, position
            FROM registrations 
            WHERE (gender = 'female' OR gender = 'Female') AND elapsed IS NOT NULL
            ORDER BY gender_pos ASC
            LIMIT 5
        """)
        for i, runner in enumerate(self.cursor.fetchall(), 1):
            results.append(f"{i}. {runner['first_name']} {runner['last_name']} - {self.format_time(runner['elapsed'])}")
        
        results.append("")
        
        # Team results
        team_results = self.calculate_team_results()
        
        # Top 2 men's teams
        results.append("=== TOP 2 MEN'S TEAMS ===")
        for i, team in enumerate(team_results['male'][:2], 1):
            results.append(f"{i}. {team['unit']} - Total Time: {self.format_time(team['total_time'])}")
            for j, runner in enumerate(team['runners'], 1):
                results.append(f"   {j}. {runner['name']} - {self.format_time(runner['elapsed'])}")
            results.append("")
        
        # Top 2 women's teams
        results.append("=== TOP 2 WOMEN'S TEAMS ===")
        for i, team in enumerate(team_results['female'][:2], 1):
            results.append(f"{i}. {team['unit']} - Total Time: {self.format_time(team['total_time'])}")
            for j, runner in enumerate(team['runners'], 1):
                results.append(f"   {j}. {runner['name']} - {self.format_time(runner['elapsed'])}")
            results.append("")
        
        # Organisational unit with most finishers
        results.append("=== MOST PARTICIPANTS (FINISHED) ===")
        self.cursor.execute("""
            SELECT organisational_unit, COUNT(*) as count
            FROM registrations 
            WHERE elapsed IS NOT NULL
            GROUP BY organisational_unit
            ORDER BY count DESC
            LIMIT 1
        """)
        result = self.cursor.fetchone()
        if result:
            results.append(f"{result['organisational_unit']}: {result['count']} finishers")
        
        results.append("")
        
        # Best effort runner (last finisher)
        results.append("=== BEST EFFORT RUNNER ===")
        self.cursor.execute("""
            SELECT first_name, last_name, elapsed
            FROM registrations 
            WHERE elapsed IS NOT NULL
            ORDER BY position DESC
            LIMIT 1
        """)
        result = self.cursor.fetchone()
        if result:
            results.append(f"{result['first_name']} {result['last_name']} - {self.format_time(result['elapsed'])}")
        
        results.append("")
        
        # Total number of runners
        self.cursor.execute("SELECT COUNT(*) as total FROM registrations WHERE elapsed IS NOT NULL")
        total_finishers = self.cursor.fetchone()['total']
        
        self.cursor.execute("SELECT COUNT(*) as total FROM registrations")
        total_registered = self.cursor.fetchone()['total']
        
        results.append("=== RACE STATISTICS ===")
        results.append(f"Total finishers: {total_finishers}")
        results.append(f"Total registered: {total_registered}")
        
        # Fastest runner overall
        results.append("")
        results.append("=== FASTEST RUNNER OVERALL ===")
        self.cursor.execute("""
            SELECT first_name, last_name, elapsed
            FROM registrations 
            WHERE elapsed IS NOT NULL
            ORDER BY elapsed ASC
            LIMIT 1
        """)
        result = self.cursor.fetchone()
        if result:
            results.append(f"{result['first_name']} {result['last_name']} - {self.format_time(result['elapsed'])}")
        
        # Output to console and file
        output = '\n'.join(results)
        print("\n" + output)
        
        with open('results.txt', 'w') as f:
            f.write(output)
        
        print(f"\nText results saved to results.txt")
        
        # Generate HTML results
        self.generate_results_html()
    
    def run(self):
        """Main program loop"""
        print("Race Results Capture System")
        print("Commands: 'start' to begin race, runner IDs to record finishes, 'stop' to generate results")
        
        try:
            while True:
                user_input = input("\n> ").strip()
                
                if user_input.lower() == 'start':
                    if self.start_time:
                        print("Race already started!")
                    else:
                        self.start_race()
                
                elif user_input.lower() == 'stop':
                    self.generate_results()
                    break
                
                elif user_input:
                    self.record_finish(user_input)
                
        except KeyboardInterrupt:
            print("\nExiting...")
        finally:
            self.conn.close()


def main():
    if len(sys.argv) != 2:
        print("Usage: python race_results.py <database_file.db>")
        sys.exit(1)
    
    db_path = sys.argv[1]
    
    try:
        race_system = RaceResultsCapture(db_path)
        race_system.run()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"Database file not found: {db_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()