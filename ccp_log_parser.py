import json
import re
from datetime import datetime
from collections import defaultdict
import matplotlib.pyplot as plt
from pathlib import Path

class CCPLogParser:
    def __init__(self, log_file_path):
        self.log_file_path = log_file_path
        self.logs = []
        self.skew_metrics = []
        self.api_metrics = []
        self.snapshots = []
        self.parse_errors = []
        
    def parse_log_file(self):
        """Parse the agent-log.txt file - expects a JSON array of log entries"""
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                # Read the entire file as JSON array
                log_data = json.load(f)
                
                if not isinstance(log_data, list):
                    print(f"✗ Error: Expected JSON array, got {type(log_data)}")
                    return
                
                print(f"📊 Found {len(log_data)} log entries in JSON array")
                
                for idx, entry in enumerate(log_data):
                    try:
                        if not isinstance(entry, dict):
                            self.parse_errors.append({
                                'index': idx,
                                'reason': f'Entry is not a dictionary: {type(entry)}',
                                'data': str(entry)[:200]
                            })
                            continue
                        
                        # Extract fields from the JSON structure
                        timestamp_str = entry.get('time', '')
                        level = entry.get('level', 'UNKNOWN')
                        component = entry.get('component', '')
                        text = entry.get('text', '')
                        line_number = entry.get('line', idx)
                        
                        # Parse timestamp
                        timestamp = None
                        if timestamp_str:
                            try:
                                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            except Exception as e:
                                self.parse_errors.append({
                                    'index': idx,
                                    'reason': f'Invalid timestamp: {e}',
                                    'timestamp': timestamp_str
                                })
                        
                        log_entry = {
                            'timestamp': timestamp,
                            'timestamp_str': timestamp_str,
                            'level': level,
                            'component': component,
                            'text': text,
                            'data': entry,  # Store entire JSON object
                            'line_number': line_number,
                            'index': idx
                        }
                        
                        self.logs.append(log_entry)
                        
                        # Extract skew metrics if present
                        if 'serverTimestamp' in entry and 'clientTimestamp' in entry:
                            self._extract_skew_metric(log_entry)
                        
                        # Extract snapshots - look for snapshot-related entries
                        if 'snapshot' in text.lower() or 'agentSnapshot' in str(entry):
                            self.snapshots.append(log_entry)
                        
                    except Exception as e:
                        self.parse_errors.append({
                            'index': idx,
                            'reason': str(e),
                            'data': str(entry)[:200]
                        })
                
                # Print parsing summary
                print(f"\n📊 Parsing Summary:")
                print(f"   Total entries: {len(log_data)}")
                print(f"   Successfully parsed: {len(self.logs)}")
                print(f"   Parse errors: {len(self.parse_errors)}")
                
                if self.parse_errors:
                    print(f"\n⚠️  Sample parsing errors (first 5):")
                    for error in self.parse_errors[:5]:
                        print(f"   Index {error['index']}: {error['reason']}")
                
        except json.JSONDecodeError as e:
            print(f"✗ Error: File is not valid JSON")
            print(f"   {str(e)}")
        except Exception as e:
            print(f"✗ Error reading file: {str(e)}")
    
    def _extract_skew_metric(self, log_entry):
        """Extract skew between client and server timestamps"""
        data = log_entry['data']
        try:
            server_ts = data.get('serverTimestamp')
            client_ts = data.get('clientTimestamp')
            
            if server_ts and client_ts:
                # Calculate skew in milliseconds
                skew = client_ts - server_ts
                
                self.skew_metrics.append({
                    'timestamp': log_entry['timestamp'],
                    'timestamp_str': log_entry['timestamp_str'],
                    'skew_ms': skew,
                    'client_timestamp': client_ts,
                    'server_timestamp': server_ts
                })
        except (ValueError, TypeError) as e:
            pass
    
    def print_sample_logs(self, count=5):
        """Print first few log entries to help debug format issues"""
        print(f"\n📄 First {min(count, len(self.logs))} log entries:")
        print("=" * 80)
        for i, log in enumerate(self.logs[:count], 1):
            print(f"\n[{i}] Index {log.get('index', 'unknown')}")
            print(f"Time: {log['timestamp_str']}")
            print(f"Level: {log['level']} | Component: {log['component']}")
            print(f"Text: {log['text'][:100]}{'...' if len(log['text']) > 100 else ''}")
            print("-" * 80)
    
    def generate_readable_output(self, output_file='ccp_logs_readable.txt'):
        """Generate a human-readable version of the logs"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("Amazon Connect CCP Log Parser - Readable Output\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Total Log Entries: {len(self.logs)}\n")
            f.write(f"Snapshots Found: {len(self.snapshots)}\n")
            f.write(f"Skew Metrics Found: {len(self.skew_metrics)}\n")
            f.write(f"Parse Errors: {len(self.parse_errors)}\n\n")
            f.write("=" * 80 + "\n\n")
            
            for idx, log in enumerate(self.logs, 1):
                f.write(f"[{idx}] {log['timestamp_str']} | {log['level']} | {log['component']}\n")
                f.write(f"Text: {log['text']}\n")
                f.write("-" * 80 + "\n")
                
                # Pretty print full JSON data
                json_str = json.dumps(log['data'], indent=2, default=str)
                f.write(json_str + "\n")
                f.write("\n" + "=" * 80 + "\n\n")
        
        print(f"✓ Readable logs saved to: {output_file}")
        return output_file
    
    def generate_html_output(self, output_file='ccp_logs_viewer.html'):
        """Generate an interactive HTML viewer for the logs"""
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>CCP Log Viewer</title>
    <style>
        body {
            font-family: 'Consolas', 'Monaco', monospace;
            background-color: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            margin: 0;
        }
        .header {
            background-color: #252526;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .header h1 {
            margin: 0 0 10px 0;
            color: #569cd6;
        }
        .stats {
            display: flex;
            gap: 30px;
            margin-top: 10px;
        }
        .stat-item {
            color: #ce9178;
        }
        .log-entry {
            background-color: #252526;
            border-left: 4px solid #007acc;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 3px;
            cursor: pointer;
        }
        .log-entry:hover {
            background-color: #2d2d30;
        }
        .log-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 5px;
        }
        .log-timestamp {
            color: #4ec9b0;
            font-weight: bold;
        }
        .log-level {
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
        }
        .log-level.INFO { background-color: #0e639c; }
        .log-level.WARN { background-color: #d16969; }
        .log-level.ERROR { background-color: #f44747; }
        .log-level.DEBUG { background-color: #6c6c6c; }
        .log-level.LOG { background-color: #4a4a4a; }
        .log-level.TRACE { background-color: #3a3a3a; }
        .log-text {
            color: #9cdcfe;
            margin-top: 5px;
            font-size: 13px;
        }
        .log-content {
            display: none;
            background-color: #1e1e1e;
            padding: 10px;
            border-radius: 3px;
            margin-top: 10px;
            overflow-x: auto;
        }
        .log-entry.expanded .log-content {
            display: block;
        }
        .expand-icon {
            color: #858585;
            margin-right: 10px;
        }
        .log-entry.expanded .expand-icon::before {
            content: '▼ ';
        }
        .log-entry:not(.expanded) .expand-icon::before {
            content: '▶ ';
        }
        pre {
            margin: 0;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .snapshot {
            border-left-color: #d7ba7d !important;
        }
        .filter-bar {
            background-color: #252526;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .filter-bar select, .filter-bar input {
            background-color: #3c3c3c;
            color: #d4d4d4;
            border: 1px solid #007acc;
            padding: 8px;
            border-radius: 3px;
            margin-right: 10px;
        }
        .component-badge {
            background-color: #3c3c3c;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 11px;
            color: #dcdcaa;
            margin-left: 10px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Amazon Connect CCP Log Parser</h1>
        <div class="stats">
            <div class="stat-item">Total Entries: <span id="total-entries">0</span></div>
            <div class="stat-item">Snapshots: <span id="total-snapshots">0</span></div>
            <div class="stat-item">Skew Metrics: <span id="total-skew">0</span></div>
            <div class="stat-item">Parse Errors: <span id="total-errors">0</span></div>
        </div>
    </div>
    
    <div class="filter-bar">
        <label>Filter by Level:</label>
        <select id="level-filter">
            <option value="all">All Levels</option>
            <option value="INFO">INFO</option>
            <option value="WARN">WARN</option>
            <option value="ERROR">ERROR</option>
            <option value="DEBUG">DEBUG</option>
            <option value="LOG">LOG</option>
            <option value="TRACE">TRACE</option>
        </select>
        <label>Search:</label>
        <input type="text" id="search-input" placeholder="Search logs...">
    </div>
    
    <div id="logs-container"></div>
    
    <script>
        const logsData = """ + json.dumps([{
            'timestamp': log['timestamp_str'],
            'level': log['level'],
            'component': log['component'],
            'text': log['text'],
            'data': log['data'],
            'index': log.get('index', 'unknown'),
            'is_snapshot': log in self.snapshots
        } for log in self.logs], default=str) + """;
        
        document.getElementById('total-entries').textContent = logsData.length;
        document.getElementById('total-snapshots').textContent = """ + str(len(self.snapshots)) + """;
        document.getElementById('total-skew').textContent = """ + str(len(self.skew_metrics)) + """;
        document.getElementById('total-errors').textContent = """ + str(len(self.parse_errors)) + """;
        
        const container = document.getElementById('logs-container');
        
        function renderLogs(filteredLogs) {
            container.innerHTML = '';
            filteredLogs.forEach((log, idx) => {
                const logDiv = document.createElement('div');
                logDiv.className = 'log-entry' + (log.is_snapshot ? ' snapshot' : '');
                logDiv.innerHTML = `
                    <div class="log-header">
                        <div>
                            <span class="expand-icon"></span>
                            <span class="log-timestamp">${log.timestamp}</span>
                            <span class="component-badge">${log.component}</span>
                        </div>
                        <span class="log-level ${log.level}">${log.level}</span>
                    </div>
                    <div class="log-text">${log.text}</div>
                    <div class="log-content">
                        <pre>${JSON.stringify(log.data, null, 2)}</pre>
                    </div>
                `;
                logDiv.addEventListener('click', () => {
                    logDiv.classList.toggle('expanded');
                });
                container.appendChild(logDiv);
            });
        }
        
        renderLogs(logsData);
        
        document.getElementById('level-filter').addEventListener('change', (e) => {
            const level = e.target.value;
            const filtered = level === 'all' ? logsData : logsData.filter(log => log.level === level);
            renderLogs(filtered);
        });
        
        document.getElementById('search-input').addEventListener('input', (e) => {
            const searchTerm = e.target.value.toLowerCase();
            const filtered = logsData.filter(log => 
                log.text.toLowerCase().includes(searchTerm) ||
                log.component.toLowerCase().includes(searchTerm) ||
                log.timestamp.toLowerCase().includes(searchTerm) ||
                JSON.stringify(log.data).toLowerCase().includes(searchTerm)
            );
            renderLogs(filtered);
        });
    </script>
</body>
</html>
        """
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✓ Interactive HTML viewer saved to: {output_file}")
        print(f"  Open this file in your browser to view logs interactively")
        return output_file
    
    def generate_skew_metrics_report(self):
        """Generate skew metrics analysis and graphs"""
        if not self.skew_metrics:
            print("⚠ No skew metrics found in logs")
            return
        
        # Calculate statistics
        skew_values = [m['skew_ms'] for m in self.skew_metrics]
        avg_skew = sum(skew_values) / len(skew_values)
        max_skew = max(skew_values)
        min_skew = min(skew_values)
        
        print("\n" + "=" * 80)
        print("SKEW METRICS ANALYSIS")
        print("=" * 80)
        print(f"Total Skew Measurements: {len(self.skew_metrics)}")
        print(f"Average Skew: {avg_skew:.2f} ms")
        print(f"Maximum Skew: {max_skew:.2f} ms")
        print(f"Minimum Skew: {min_skew:.2f} ms")
        print("=" * 80 + "\n")
        
        # Generate graphs
        self._plot_skew_over_time()
        self._plot_skew_distribution()
    
    def _plot_skew_over_time(self):
        """Plot skew metrics over time"""
        if not self.skew_metrics:
            return
        
        timestamps = [m['timestamp'] for m in self.skew_metrics]
        skew_values = [m['skew_ms'] for m in self.skew_metrics]
        
        plt.figure(figsize=(12, 6))
        plt.plot(timestamps, skew_values, marker='o', linestyle='-', linewidth=1, markersize=3)
        plt.title('Client-Server Clock Skew Over Time', fontsize=14, fontweight='bold')
        plt.xlabel('Timestamp', fontsize=12)
        plt.ylabel('Skew (milliseconds)', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        output_file = 'skew_over_time.png'
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"✓ Skew over time graph saved to: {output_file}")
    
    def _plot_skew_distribution(self):
        """Plot skew distribution histogram"""
        if not self.skew_metrics:
            return
        
        skew_values = [m['skew_ms'] for m in self.skew_metrics]
        
        plt.figure(figsize=(10, 6))
        plt.hist(skew_values, bins=30, color='#007acc', alpha=0.7, edgecolor='black')
        plt.title('Clock Skew Distribution', fontsize=14, fontweight='bold')
        plt.xlabel('Skew (milliseconds)', fontsize=12)
        plt.ylabel('Frequency', fontsize=12)
        plt.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        
        output_file = 'skew_distribution.png'
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"✓ Skew distribution graph saved to: {output_file}")


def list_log_files(directory_path):
    """List all log files in the specified directory"""
    directory = Path(directory_path)
    
    if not directory.exists():
        print(f"✗ Error: Directory not found: {directory_path}")
        return []
    
    # Get all .txt and .log files (common log file extensions)
    log_files = []
    for file_path in directory.iterdir():
        if file_path.is_file() and file_path.suffix in ['.txt', '.log']:
            log_files.append(file_path)
    
    return sorted(log_files)


def display_file_menu(files):
    """Display an interactive menu for file selection"""
    if not files:
        return None
    
    print("\n" + "=" * 80)
    print("Available Log Files:")
    print("=" * 80)
    
    for idx, file_path in enumerate(files, 1):
        # Get file size and modification time
        file_size = file_path.stat().st_size
        mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
        
        # Format file size
        if file_size < 1024:
            size_str = f"{file_size} B"
        elif file_size < 1024 * 1024:
            size_str = f"{file_size / 1024:.1f} KB"
        else:
            size_str = f"{file_size / (1024 * 1024):.1f} MB"
        
        print(f"  [{idx}] {file_path.name}")
        print(f"      Size: {size_str} | Modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("=" * 80)
    
    while True:
        try:
            choice = input("\nEnter file number to parse (or 'q' to quit): ").strip()
            
            if choice.lower() == 'q':
                return None
            
            file_num = int(choice)
            if 1 <= file_num <= len(files):
                return files[file_num - 1]
            else:
                print(f"✗ Invalid selection. Please enter a number between 1 and {len(files)}")
        except ValueError:
            print("✗ Invalid input. Please enter a number or 'q' to quit")


def main():
    print("\n" + "=" * 80)
    print("Amazon Connect CCP Log Parser - Local Edition")
    print("=" * 80 + "\n")
    
    # Use relative path - finds agentLogsToParse directory next to the script
    script_dir = Path(__file__).parent
    DEFAULT_LOG_DIRECTORY = script_dir / "agentLogsToParse"
    
    print(f"📂 Scanning directory: {DEFAULT_LOG_DIRECTORY}")
    
    # List all log files in the directory
    log_files = list_log_files(DEFAULT_LOG_DIRECTORY)
    
    if not log_files:
        print("✗ No log files found in the directory")
        print("   Supported file types: .txt, .log")
        return
    
    print(f"✓ Found {len(log_files)} log file(s)")
    
    # Display menu and get user selection
    selected_file = display_file_menu(log_files)
    
    if selected_file is None:
        print("\n👋 Goodbye!")
        return
    
    print(f"\n📂 Selected file: {selected_file.name}")
    
    # Parse logs
    parser = CCPLogParser(selected_file)
    print("⚙ Parsing JSON log file...")
    parser.parse_log_file()
    
    # Show sample logs to help debug
    if parser.logs:
        parser.print_sample_logs(3)
    
    print(f"\n✓ Total log entries: {len(parser.logs)}")
    print(f"✓ Agent snapshots: {len(parser.snapshots)}")
    print(f"✓ Skew measurements: {len(parser.skew_metrics)}\n")
    
    # Generate outputs
    print("📝 Generating readable text output...")
    parser.generate_readable_output()
    
    print("\n🌐 Generating interactive HTML viewer...")
    parser.generate_html_output()
    
    if parser.skew_metrics:
        print("\n📊 Generating skew metrics analysis...")
        parser.generate_skew_metrics_report()
    
    print("\n" + "=" * 80)
    print("✓ Processing complete!")
    print("=" * 80)
    print("\nGenerated files:")
    print("  - ccp_logs_readable.txt (text format)")
    print("  - ccp_logs_viewer.html (interactive browser viewer)")
    if parser.skew_metrics:
        print("  - skew_over_time.png (graph)")
        print("  - skew_distribution.png (graph)")
    print("\n")


if __name__ == "__main__":
    main()
