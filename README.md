# Amazon Connect CCP Log Parser - Local Edition

A Python tool for parsing and analyzing Amazon Connect Contact Control Panel (CCP) logs locally on your machine. This tool provides readable log output, interactive HTML viewing, and skew metrics visualization with robust error handling and debugging capabilities.

## Overview

This script mirrors the functionality of Amazon's online CCP Log Parser tool, but runs entirely offline on your local machine for enhanced data privacy and convenience. It processes CCP `agent-log.txt` files (JSON format) to extract structured log data, calculate client-server clock skew metrics, and generate visual reports.

## Features

- **Automatic File Discovery**: Scans a designated directory and presents an interactive menu to select log files
- **JSON Array Parsing**: Handles CCP's native JSON array log format with proper field extraction
- **Component-Based Filtering**: View logs by component (ccp, SharedWorker, CRM, etc.)
- **Parse Error Tracking**: Identifies and reports entries that couldn't be parsed with detailed error information
- **Readable Text Output**: Generates a formatted text file with all log entries and expanded JSON data
- **Interactive HTML Viewer**: Creates a browser-based log viewer with filtering, search, collapsible entries, and component badges
- **Skew Metrics Analysis**: Calculates and visualizes client-server timestamp differences (when available)
- **Debug Information**: Shows parsing summary and sample log entries to help troubleshoot format issues
- **Offline Processing**: All data processing happens locally—no external API calls or data uploads

## Prerequisites

- Python 3.7+
- matplotlib library

## Installation

1. **Clone or download this repository**

    git clone [https://github.com/zendesk-jakelunn/local-amazon-connect-ccp-log-parser.git]
    cd amazon-connect-ccp-log-parser

2. **Create a virtual environment** (recommended to avoid Homebrew Python conflicts):

    python3 -m venv venv  
    source venv/bin/activate

3. **Install dependencies**:

    pip install matplotlib

## Directory Structure Create the following directory structure:

    amazon-connect-ccp-log-parser/  
    ├── ccp_log_parser.py  
    ├── README.md  
    ├── agentLogsToParse/  
    │ ├── agent-log-1.txt  
    │ ├── agent-log-2.txt  
    │ └── ...  
    └── venv/
Place all CCP log files you want to analyze in the `agentLogsToParse/` directory. 

## CCP Log Format
This parser expects CCP log files in **JSON array format**, where each entry is a JSON object with the following structure:

    {
    "component": "ccp",
    "level": "LOG",
    "text": "[UserMediaProvider] getUserMedia called",
    "time": "2025-10-24T22:58:26.721Z",
    "tabId": "123etc123etc",
    "exception": null,
    "objects":
    [],
    "line": 170,
    "agentResourceId": "123etc123etc",
    "loggerId": "123etc123etc",
    "contextLayer": "CCP"
    }

This is the native format exported from Amazon Connect's CCP log download feature.

## Usage

1. **Activate your virtual environment** (if using one):

    source venv/bin/activate

2. **Run the script**:

    python ccp_log_parser.py


3. **Select a log file** from the interactive menu by entering its number

4. **Review the parsing summary** displayed in the terminal:
   - Total JSON entries found
   - Successfully parsed entries
   - Parse errors (if any)
   - Sample log entries showing extracted data

5. **Review the generated outputs**:
   - `ccp_logs_readable.txt` - Plain text formatted logs
   - `ccp_logs_viewer.html` - Interactive browser-based viewer
   - `skew_over_time.png` - Graph showing clock skew over time (if skew data exists)
   - `skew_distribution.png` - Histogram of skew distribution (if skew data exists)

## Output Files

### ccp_logs_readable.txt

A human-readable text file containing:
- Total log entries, snapshots, skew metrics, and parse errors
- All log entries with timestamps, levels, components, and log text
- Full JSON data for each entry, pretty-printed for readability

### ccp_logs_viewer.html

An interactive HTML page featuring:
- Collapsible log entries with component badges (ccp, SharedWorker, etc.)
- Log text displayed prominently for quick scanning
- Filter by log level (INFO, WARN, ERROR, DEBUG, LOG, TRACE)
- Full-text search across all log fields
- Color-coded log levels
- Dark theme optimized for extended viewing
- Parse error count in the header

### Skew Metrics Graphs

- **skew_over_time.png**: Line graph showing client-server timestamp differences throughout the session
- **skew_distribution.png**: Histogram showing the frequency distribution of skew values

**Note**: Skew metrics are only generated if your logs contain `serverTimestamp` and `clientTimestamp` fields.

## Configuration

To change the default log directory, edit the `DEFAULT_LOG_DIRECTORY` variable in the `main()` function:

DEFAULT_LOG_DIRECTORY = "/path/to/your/log/directory"(this repo contains a directory named `agentLogsToParse` as a default location to store logs to be parsed)

## Troubleshooting

### ModuleNotFoundError: No module named 'matplotlib'

**Solution**: Ensure you've activated your virtual environment and run:

    source venv/bin/activate  
    pip install matplotlib


### No log files found

**Possible causes**:
- Log files are not in the `agentLogsToParse/` directory
- Files don't have `.txt` or `.log` extensions

**Solution**: Verify log files are in the correct directory with supported extensions

### "File is not valid JSON" error

**Possible causes**:
- Log file is corrupted or incomplete
- Log file is not in JSON format
- File was downloaded incorrectly

**Solution**: 
1. Download a fresh copy of the log from Amazon Connect CCP
2. Verify the file opens correctly in a text editor
3. Check that the file starts with `[` and ends with `]`

### Empty or minimal parsing results

**Possible causes**:
- Log file structure doesn't match expected JSON format
- JSON entries are missing expected fields

**Solution**: 
1. Check the parsing summary displayed in the terminal
2. Review the "First 3 log entries" output to see what was extracted
3. Open `ccp_logs_readable.txt` to see parse errors and their indices
4. Verify your log file format matches the expected structure (see "CCP Log Format" section above)

### No skew metrics found

**Explanation**: This is normal! Most CCP logs don't contain skew data unless specific timing/debugging features are enabled. The tool will still generate readable logs and the HTML viewer successfully.

### Parse errors showing in output

**Explanation**: The tool tracks JSON entries it couldn't parse and displays them for transparency. Check the parsing summary and `ccp_logs_readable.txt` for details on which entries had issues.

## Understanding the Output

**Parsing Summary**: Displayed when running the script, shows:
- How many JSON entries were in the log file
- How many were successfully parsed
- How many had parsing errors

**Sample Log Entries**: The first 3 parsed entries are displayed to help verify the parser understood your log format correctly. You'll see:
- Timestamp
- Log level (INFO, LOG, TRACE, etc.)
- Component (ccp, SharedWorker, etc.)
- Log text message

**Component Types**: CCP logs contain entries from different components:
- `ccp`: Main Contact Control Panel events
- `SharedWorker`: Background worker process events
- `CRM`: Customer Relationship Management integration events

## Requirements

- Python 3.7+
- matplotlib 3.0+

## License

This tool is provided as-is for local use with Amazon Connect CCP logs. There is no guarantee this will work for all situations. 

If you have questions, feel free to reach out to Jake Lunn :D