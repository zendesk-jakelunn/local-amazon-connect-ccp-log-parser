import json
import logging
import re
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any, Optional
import matplotlib.pyplot as plt
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'  # Simple format for user-facing messages
)
logger = logging.getLogger(__name__)

class CCPLogParser:
    """Parser for Amazon Connect CCP log files in JSON format.

    This class handles parsing, analysis, and visualization of CCP logs,
    including extracting metrics, generating reports, and creating interactive viewers.

    Attributes:
        log_file_path: Path to the log file to parse
        logs: List of successfully parsed log entries
        skew_metrics: List of client-server timestamp skew measurements
        api_metrics: List of API call metrics (reserved for future use)
        snapshots: List of agent snapshot entries
        parse_errors: List of entries that failed to parse with error details
    """

    def __init__(self, log_file_path: Path) -> None:
        """Initialize the parser with a log file path.

        Args:
            log_file_path: Path object pointing to the log file to parse
        """
        self.log_file_path: Path = log_file_path
        self.logs: List[Dict[str, Any]] = []
        self.skew_metrics: List[Dict[str, Any]] = []
        self.api_metrics: List[Dict[str, Any]] = []
        self.snapshots: List[Dict[str, Any]] = []
        self.parse_errors: List[Dict[str, Any]] = []
        
    def parse_log_file(self) -> None:
        """Parse the agent-log.txt file - expects a JSON array of log entries.

        Reads the log file as a JSON array and extracts structured information from each entry.
        Populates the logs, snapshots, and skew_metrics lists, and tracks any parsing errors.

        The method prints progress information and a summary of parsing results to stdout.
        """
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                # Read the entire file as JSON array
                log_data = json.load(f)
                
                if not isinstance(log_data, list):
                    logger.error(f"✗ Error: Expected JSON array, got {type(log_data)}")
                    return

                logger.info(f"📊 Found {len(log_data)} log entries in JSON array")
                
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
                
                # Log parsing summary
                logger.info(f"\n📊 Parsing Summary:")
                logger.info(f"   Total entries: {len(log_data)}")
                logger.info(f"   Successfully parsed: {len(self.logs)}")
                logger.info(f"   Parse errors: {len(self.parse_errors)}")

                if self.parse_errors:
                    logger.warning(f"\n⚠️  Sample parsing errors (first 5):")
                    for error in self.parse_errors[:5]:
                        logger.warning(f"   Index {error['index']}: {error['reason']}")
                
        except json.JSONDecodeError as e:
            logger.error(f"✗ Error: File is not valid JSON")
            logger.error(f"   {str(e)}")
        except Exception as e:
            logger.error(f"✗ Error reading file: {str(e)}")
    
    def _extract_skew_metric(self, log_entry: Dict[str, Any]) -> None:
        """Extract and calculate skew between client and server timestamps.

        Args:
            log_entry: Parsed log entry dictionary containing 'data' with timestamps

        The method calculates the difference between client and server timestamps
        and appends the result to skew_metrics if both timestamps are present.
        """
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
    
    def print_sample_logs(self, count: int = 5) -> None:
        """Print first few log entries to help debug format issues.

        Args:
            count: Number of log entries to display (default: 5)

        Prints a formatted preview of the first N log entries to stdout,
        including timestamp, level, component, and truncated text.
        """
        logger.info(f"\n📄 First {min(count, len(self.logs))} log entries:")
        logger.info("=" * 80)
        for i, log in enumerate(self.logs[:count], 1):
            logger.info(f"\n[{i}] Index {log.get('index', 'unknown')}")
            logger.info(f"Time: {log['timestamp_str']}")
            logger.info(f"Level: {log['level']} | Component: {log['component']}")
            logger.info(f"Text: {log['text'][:100]}{'...' if len(log['text']) > 100 else ''}")
            logger.info("-" * 80)
    
    def generate_readable_output(self, output_file: str = 'ccp_logs_readable.txt') -> str:
        """Generate a human-readable text version of the logs.

        Args:
            output_file: Path where the readable log file should be saved (default: 'ccp_logs_readable.txt')

        Returns:
            Path to the generated output file

        Creates a formatted text file with log statistics, all log entries with their
        full JSON data, and parsing error information.
        """
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
        
        logger.info(f"✓ Readable logs saved to: {output_file}")
        return output_file
    
    def generate_html_output(self, output_file: str = 'ccp_logs_viewer.html') -> str:
        """Generate an interactive HTML viewer for the logs.

        Args:
            output_file: Path where the HTML file should be saved (default: 'ccp_logs_viewer.html')

        Returns:
            Path to the generated HTML file

        Creates a self-contained HTML file with embedded JavaScript for interactive
        log viewing, including filtering by level, full-text search, collapsible entries,
        and a dark theme interface.
        """
        # Read template file
        template_path = Path(__file__).parent / 'template_log_viewer.html'

        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                html_template = f.read()
        except FileNotFoundError:
            logger.warning(f"⚠ Warning: Template file not found at {template_path}")
            logger.warning("  Falling back to embedded template")
            # Fallback to basic template if file is missing
            html_template = self._get_fallback_template()

        # Prepare log data for JSON serialization
        logs_data = json.dumps([{
            'timestamp': log['timestamp_str'],
            'level': log['level'],
            'component': log['component'],
            'text': log['text'],
            'data': log['data'],
            'index': log.get('index', 'unknown'),
            'is_snapshot': log in self.snapshots
        } for log in self.logs], default=str)

        # Replace placeholders with actual data
        html_content = html_template.replace('{LOGS_DATA}', logs_data)
        html_content = html_content.replace('{TOTAL_SNAPSHOTS}', str(len(self.snapshots)))
        html_content = html_content.replace('{TOTAL_SKEW}', str(len(self.skew_metrics)))
        html_content = html_content.replace('{TOTAL_ERRORS}', str(len(self.parse_errors)))

        # Write output file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"✓ Interactive HTML viewer saved to: {output_file}")
        logger.info(f"  Open this file in your browser to view logs interactively")
        return output_file

    def _get_fallback_template(self) -> str:
        """Return a minimal fallback HTML template if template file is missing.

        Returns:
            Basic HTML template string with placeholders
        """
        return """<!DOCTYPE html>
<html>
<head>
    <title>CCP Log Viewer</title>
    <style>body { font-family: monospace; padding: 20px; }</style>
</head>
<body>
    <h1>CCP Log Viewer (Fallback Mode)</h1>
    <p>Template file missing. Showing basic view.</p>
    <pre id="logs"></pre>
    <script>
        const logsData = {LOGS_DATA};
        document.getElementById('logs').textContent = JSON.stringify(logsData, null, 2);
    </script>
</body>
</html>"""
    
    def generate_skew_metrics_report(self) -> None:
        """Generate skew metrics analysis and graphs.

        Calculates statistics (average, min, max) for clock skew measurements
        and generates visualization graphs. Prints results to stdout and saves
        PNG files for time series and distribution plots.

        Only executes if skew_metrics list contains data.
        """
        if not self.skew_metrics:
            logger.warning("⚠ No skew metrics found in logs")
            return

        # Calculate statistics
        skew_values = [m['skew_ms'] for m in self.skew_metrics]
        avg_skew = sum(skew_values) / len(skew_values)
        max_skew = max(skew_values)
        min_skew = min(skew_values)

        logger.info("\n" + "=" * 80)
        logger.info("SKEW METRICS ANALYSIS")
        logger.info("=" * 80)
        logger.info(f"Total Skew Measurements: {len(self.skew_metrics)}")
        logger.info(f"Average Skew: {avg_skew:.2f} ms")
        logger.info(f"Maximum Skew: {max_skew:.2f} ms")
        logger.info(f"Minimum Skew: {min_skew:.2f} ms")
        logger.info("=" * 80 + "\n")
        
        # Generate graphs
        self._plot_skew_over_time()
        self._plot_skew_distribution()
    
    def _plot_skew_over_time(self) -> None:
        """Generate and save a line graph of skew metrics over time.

        Creates a time series plot showing client-server clock skew throughout
        the log session. Saves the result as 'skew_over_time.png'.
        """
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
        
        logger.info(f"✓ Skew over time graph saved to: {output_file}")
    
    def _plot_skew_distribution(self) -> None:
        """Generate and save a histogram of skew value distribution.

        Creates a histogram showing the frequency distribution of clock skew values.
        Saves the result as 'skew_distribution.png'.
        """
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
        
        logger.info(f"✓ Skew distribution graph saved to: {output_file}")


def list_log_files(directory_path: Path) -> List[Path]:
    """List all log files in the specified directory.

    Args:
        directory_path: Path object pointing to the directory to scan

    Returns:
        Sorted list of Path objects for .txt and .log files found in the directory,
        or empty list if directory doesn't exist
    """
    directory = Path(directory_path)
    
    if not directory.exists():
        logger.error(f"✗ Error: Directory not found: {directory_path}")
        return []
    
    # Get all .txt and .log files (common log file extensions)
    log_files = []
    for file_path in directory.iterdir():
        if file_path.is_file() and file_path.suffix in ['.txt', '.log']:
            log_files.append(file_path)
    
    return sorted(log_files)


def display_file_menu(files: List[Path]) -> Optional[Path]:
    """Display an interactive menu for file selection.

    Args:
        files: List of Path objects representing available log files

    Returns:
        Selected Path object, or None if user quits or no files available

    Displays file information (name, size, modification time) and prompts
    the user to select a file by number.
    """
    if not files:
        return None
    
    logger.info("\n" + "=" * 80)
    logger.info("Available Log Files:")
    logger.info("=" * 80)

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

        logger.info(f"  [{idx}] {file_path.name}")
        logger.info(f"      Size: {size_str} | Modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")

    logger.info("=" * 80)
    
    while True:
        try:
            choice = input("\nEnter file number to parse (or 'q' to quit): ").strip()
            
            if choice.lower() == 'q':
                return None
            
            file_num = int(choice)
            if 1 <= file_num <= len(files):
                return files[file_num - 1]
            else:
                logger.error(f"✗ Invalid selection. Please enter a number between 1 and {len(files)}")
        except ValueError:
            logger.error("✗ Invalid input. Please enter a number or 'q' to quit")


def main() -> None:
    """Main entry point for the CCP log parser.

    Orchestrates the entire parsing workflow:
    1. Scans for log files in the default directory
    2. Presents interactive menu for file selection
    3. Parses the selected log file
    4. Generates all output formats (text, HTML, graphs)
    5. Displays summary of generated files
    """
    logger.info("\n" + "=" * 80)
    logger.info("Amazon Connect CCP Log Parser - Local Edition")
    logger.info("=" * 80 + "\n")

    # Use relative path - finds agentLogsToParse directory next to the script
    script_dir = Path(__file__).parent
    DEFAULT_LOG_DIRECTORY = script_dir / "agentLogsToParse"

    logger.info(f"📂 Scanning directory: {DEFAULT_LOG_DIRECTORY}")

    # List all log files in the directory
    log_files = list_log_files(DEFAULT_LOG_DIRECTORY)

    if not log_files:
        logger.error("✗ No log files found in the directory")
        logger.error("   Supported file types: .txt, .log")
        return

    logger.info(f"✓ Found {len(log_files)} log file(s)")

    # Display menu and get user selection
    selected_file = display_file_menu(log_files)

    if selected_file is None:
        logger.info("\n👋 Goodbye!")
        return

    logger.info(f"\n📂 Selected file: {selected_file.name}")

    # Parse logs
    parser = CCPLogParser(selected_file)
    logger.info("⚙ Parsing JSON log file...")
    parser.parse_log_file()

    # Show sample logs to help debug
    if parser.logs:
        parser.print_sample_logs(3)

    logger.info(f"\n✓ Total log entries: {len(parser.logs)}")
    logger.info(f"✓ Agent snapshots: {len(parser.snapshots)}")
    logger.info(f"✓ Skew measurements: {len(parser.skew_metrics)}\n")

    # Generate outputs
    logger.info("📝 Generating readable text output...")
    parser.generate_readable_output()

    logger.info("\n🌐 Generating interactive HTML viewer...")
    parser.generate_html_output()

    if parser.skew_metrics:
        logger.info("\n📊 Generating skew metrics analysis...")
        parser.generate_skew_metrics_report()

    logger.info("\n" + "=" * 80)
    logger.info("✓ Processing complete!")
    logger.info("=" * 80)
    logger.info("\nGenerated files:")
    logger.info("  - ccp_logs_readable.txt (text format)")
    logger.info("  - ccp_logs_viewer.html (interactive browser viewer)")
    if parser.skew_metrics:
        logger.info("  - skew_over_time.png (graph)")
        logger.info("  - skew_distribution.png (graph)")
    logger.info("\n")


if __name__ == "__main__":
    main()
