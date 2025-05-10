---
description: Analyze QuantConnect algorithm logs and suggest fixes based on documentation
---
# Simple QuantConnect Algorithm Debug Workflow

This workflow analyzes algorithm code and logs to identify issues and suggest fixes based on documentation.

## 1. Select algorithm and log files
- id: algorithm_file
- type: file
- prompt: Select the algorithm file to analyze (main.py):

- id: log_file
- type: file
- prompt: Select the log file to analyze:

## 2. Analyze algorithm and logs
```bash
ALGORITHM_FILE="{{ algorithm_file }}"
LOG_FILE="{{ log_file }}"

echo "=== ANALYZING ALGORITHM: $(basename $ALGORITHM_FILE) ==="
echo "=== LOG FILE: $(basename $LOG_FILE) ==="

# Extract key algorithm components
echo -e "\n=== ALGORITHM STRUCTURE ==="
grep -n "class\|def\|self.add_\|self.set_" "$ALGORITHM_FILE" | head -20

# Extract errors and warnings from logs
echo -e "\n=== ERRORS AND WARNINGS ==="
grep -i "error\|exception\|warning\|failed" "$LOG_FILE" | grep -v "\[IMPORTANT\]"

# Check for data subscription issues
echo -e "\n=== DATA SUBSCRIPTION ISSUES ==="
grep -i "no data\|subscription\|universe" "$LOG_FILE" | grep -i "error\|warning\|failed"

# Check for order execution issues
echo -e "\n=== ORDER EXECUTION ISSUES ==="
grep -i "order\|trade\|fill" "$LOG_FILE" | grep -i "error\|warning\|failed"

# Show important messages
echo -e "\n=== IMPORTANT MESSAGES ==="
grep "\[IMPORTANT\]" "$LOG_FILE" | head -10

# Extract algorithm statistics
echo -e "\n=== ALGORITHM STATISTICS ==="
grep "Algorithm Id\|completed in" "$LOG_FILE"

# Extract critical error (first error found)
CRITICAL_ERROR=$(grep -i "error\|exception" "$LOG_FILE" | grep -v "\[IMPORTANT\]" | head -1)
if [ ! -z "$CRITICAL_ERROR" ]; then
  echo -e "\n=== CRITICAL ERROR IDENTIFIED ==="
  echo "$CRITICAL_ERROR"
  
  # Extract search term from error message
  SEARCH_TERM=$(echo "$CRITICAL_ERROR" | sed -E 's/^.*\[ERROR\]\s*//g' | cut -d':' -f1 | head -c 50)
  if [ -z "$SEARCH_TERM" ]; then
    # Try another pattern if the first one didn't work
    SEARCH_TERM=$(echo "$CRITICAL_ERROR" | grep -o -E '[A-Za-z0-9]+Exception|Error[A-Za-z0-9]*' | head -1)
  fi
  
  if [ ! -z "$SEARCH_TERM" ]; then
    echo -e "\n=== SUGGESTED DOCUMENTATION SEARCH: $SEARCH_TERM ==="
  fi
fi
```

## 3. Research documentation
- id: search_term
- type: text
- prompt: Enter the error or issue to research (use suggested term or enter your own):

```bash
echo -e "\n=== SEARCHING DOCUMENTATION FOR: {{ search_term }} ==="

# Search documentation repositories
echo -e "\nQuantConnect Documentation results:"
grep -r --include="*.md" --include="*.py" "{{ search_term }}" /Users/overton/CascadeProjects/QuantConnect\ Trading\ Algorithms/.windsurf/QC-Doc-Repos/Documentation | head -5

echo -e "\nLean Engine examples:"
find /Users/overton/CascadeProjects/QuantConnect\ Trading\ Algorithms/.windsurf/QC-Doc-Repos/Lean/Algorithm.Python -type f -name "*.py" -exec grep -l "{{ search_term }}" {} \; | head -3

# If examples were found, show the first one
EXAMPLE_FILE=$(find /Users/overton/CascadeProjects/QuantConnect\ Trading\ Algorithms/.windsurf/QC-Doc-Repos/Lean/Algorithm.Python -type f -name "*.py" -exec grep -l "{{ search_term }}" {} \; | head -1)
if [ ! -z "$EXAMPLE_FILE" ]; then
  echo -e "\n=== EXAMPLE CODE FROM: $(basename $EXAMPLE_FILE) ==="
  grep -A 10 -B 10 "{{ search_term }}" "$EXAMPLE_FILE" | head -20
fi
```

## 4. Suggest fixes
- id: fix_suggestion
- type: multiline
- prompt: Based on the analysis and documentation, describe the issue and suggested fix:

```bash
echo -e "\n=== ISSUE SUMMARY AND FIX SUGGESTION ==="
echo "{{ fix_suggestion }}"

echo -e "\nTo implement this fix, edit: $ALGORITHM_FILE"
```

## Notes
- This workflow focuses on analysis rather than file management
- It analyzes both algorithm code and log files to identify issues
- It searches documentation repositories for solutions
- It provides example code from similar algorithms when available
- The workflow is designed to be simple and straightforward
