# QuantConnect Logs Automation with Playwright

## Overview
This project automates the process of downloading backtest logs and order history from QuantConnect using Playwright, a Node.js library for browser automation. The primary goal is to streamline the retrieval of backtest data for analysis and record-keeping.

## Problem Statement
QuantConnect's web interface requires manual navigation to access and download backtest logs and order history. For users running multiple backtests or needing to maintain comprehensive records, this manual process can be time-consuming and inefficient.

## Solution
This automation solution provides:
- Automated login to QuantConnect (with session persistence)
- Navigation to specific backtest results
- Automated downloading of logs and order history
- Organized storage of downloaded files
- Error handling and debugging capabilities

## Key Features

### 1. Session Management
- Uses `qc_auth.json` to store authentication cookies for persistent login
- Maintains user session across multiple runs
- Handles authentication state to prevent repeated logins

### 2. Backtest Data Retrieval
- Downloads detailed backtest logs in text format
- Retrieves order history in CSV format
- Organizes files with descriptive names based on backtest ID

### 3. Error Handling
- Comprehensive error detection and reporting
- Screenshot capture on failure for debugging
- Retry mechanisms for unreliable operations

### 4. Debugging Tools
- Detailed logging of all operations
- Visual feedback during execution
- Screenshot capture at critical points

## File Structure

- `download_backtest_data.py` - Main automation script that handles the entire workflow
- `qc_auth.json` - Stores authentication cookies for persistent login (DO NOT COMMIT)
- `playwright_user_data/` - Contains browser profile and session data
- `downloads/` - Automatically created directory for storing downloaded backtest logs and order history

## Usage

1. Install dependencies:
   ```bash
   pip install playwright
   playwright install
   ```

2. Run the automation:
   ```bash
   python download_backtest_data.py "https://www.quantconnect.com/project/YOUR_BACKTEST_URL"
   ```

3. The script will:
   - Open a browser window (visible by default for debugging)
   - Navigate to the specified backtest
   - Download logs and order history
   - Save files to the `downloads` directory

## Security Notes

- `qc_auth.json` contains sensitive authentication data
- Never commit this file to version control
- The file is included in `.gitignore` by default

## Troubleshooting

1. **Authentication Issues**
   - Delete `qc_auth.json` and run the script again to re-authenticate
   - Ensure your QuantConnect credentials are correct

2. **Element Not Found Errors**
   - The script includes multiple selectors for reliability
   - Check console output for detailed error messages
   - Screenshots are saved in the `debug` directory when errors occur

3. **Download Failures**
   - Verify the download directory is writable
   - Check for any browser popup blockers
   - Ensure sufficient disk space is available

## Future Enhancements

- [ ] Support for batch processing multiple backtests
- [ ] Headless mode for production use
- [ ] Integration with QuantConnect API (if available)
- [ ] Automated backup of downloaded files
- [ ] Email notifications for completed downloads

## Dependencies

- Python 3.7+
- Playwright
- Required Python packages (see `requirements.txt`)

## License

This project is for personal use only. Unauthorized distribution or use may violate QuantConnect's terms of service.
