---
description: Research QuantConnect documentation repositories for implementation guidance or problem-solving
---

# WARNING: DO NOT MODIFY THIS FILE WITHOUT EXPLICIT USER PERMISSION
# QuantConnect Documentation Research Workflow

This workflow systematically searches through local QuantConnect documentation repositories to find relevant information for implementing new features or solving problems.

## 1. Define the problem or feature
- id: problem_description
- type: multiline
- prompt: Describe the problem you're trying to solve or the feature you want to implement in simple English:

## 2. Identify relevant components
- id: components
- type: select
- options: ["Algorithm Structure", "Data Subscriptions", "Option Chains", "Universe Selection", "Order Management", "Portfolio Construction", "Risk Management", "Scheduling", "Indicators", "Deployment", "Backtesting", "Live Trading", "Other"]
- prompt: Which component of QuantConnect is most relevant to your problem/feature?

## 3. Specify asset classes (if applicable)
- id: asset_classes
- type: multiselect
- options: ["Equities", "Options", "Futures", "Future Options", "Forex", "Crypto", "CFDs", "Index Options", "Multiple", "N/A"]
- prompt: Which asset classes are involved? (Select multiple if needed)

## 4. Search primary documentation
```bash
echo "Searching primary QuantConnect documentation for relevant information..."
echo "=============================================================="

# Search in Documentation repository
grep -r --include="*.md" --include="*.html" --include="*.py" "{{ problem_description }}" /Users/overton/CascadeProjects/QuantConnect\ Trading\ Algorithms/.windsurf/QC-Doc-Repos/Documentation | head -n 20
```

## 5. Search deployment interface documentation
```bash
echo "Searching Lean CLI documentation for deployment and interface information..."
echo "=============================================================="

# Search in lean-cli repository
grep -r --include="*.md" --include="*.py" "{{ problem_description }}" /Users/overton/CascadeProjects/QuantConnect\ Trading\ Algorithms/.windsurf/QC-Doc-Repos/lean-cli | head -n 20
```

## 6. Search engine implementation
```bash
echo "Searching Lean engine implementation for technical details..."
echo "=============================================================="

# Search in Lean repository
grep -r --include="*.py" "{{ components }}" /Users/overton/CascadeProjects/QuantConnect\ Trading\ Algorithms/.windsurf/QC-Doc-Repos/Lean/Algorithm.Python | head -n 20
```

## 7. Find example algorithms
```bash
echo "Finding example algorithms related to your problem/feature..."
echo "=============================================================="

# Search for example algorithms in Lean repository
find /Users/overton/CascadeProjects/QuantConnect\ Trading\ Algorithms/.windsurf/QC-Doc-Repos/Lean/Algorithm.Python -type f -name "*{{ components }}*.py" -o -name "*{{ asset_classes }}*.py" | head -n 10

# Display first example if found
FIRST_EXAMPLE=$(find /Users/overton/CascadeProjects/QuantConnect\ Trading\ Algorithms/.windsurf/QC-Doc-Repos/Lean/Algorithm.Python -type f -name "*{{ components }}*.py" -o -name "*{{ asset_classes }}*.py" | head -n 1)
if [ ! -z "$FIRST_EXAMPLE" ]; then
  echo "First example algorithm:"
  echo "=============================================================="
  cat "$FIRST_EXAMPLE" | head -n 50
  echo "..."
fi
```

## 8. Search for common issues and solutions
```bash
echo "Searching for common issues and solutions related to your problem..."
echo "=============================================================="

# Search for error messages or common issues
grep -r --include="*.md" --include="*.py" "error.*{{ problem_description }}" /Users/overton/CascadeProjects/QuantConnect\ Trading\ Algorithms/.windsurf/QC-Doc-Repos/Documentation | head -n 10
```

## 9. Summarize findings
- id: summary
- type: multiline
- prompt: Based on the documentation search, what are the key findings and recommended approaches for your problem/feature?

## 10. Create implementation notes
```bash
# Create implementation notes document
mkdir -p /Users/overton/CascadeProjects/QuantConnect\ Trading\ Algorithms/.windsurf/implementation-notes
cat > "/Users/overton/CascadeProjects/QuantConnect Trading Algorithms/.windsurf/implementation-notes/$(date +%Y%m%d)-{{ components }}.md" << 'EOF'
# Implementation Notes: {{ components }}

## Problem/Feature Description
{{ problem_description }}

## Documentation Research Summary
{{ summary }}

## Key Code Examples

```python
# Add relevant code examples here based on documentation findings
```

## Implementation Approach
1. 
2. 
3. 

## References
- [Documentation Repository](/Users/overton/CascadeProjects/QuantConnect Trading Algorithms/.windsurf/QC-Doc-Repos/Documentation)
- [Lean CLI Repository](/Users/overton/CascadeProjects/QuantConnect Trading Algorithms/.windsurf/QC-Doc-Repos/lean-cli)
- [Lean Engine Repository](/Users/overton/CascadeProjects/QuantConnect Trading Algorithms/.windsurf/QC-Doc-Repos/Lean)

EOF

echo "Implementation notes created at: /Users/overton/CascadeProjects/QuantConnect Trading Algorithms/.windsurf/implementation-notes/$(date +%Y%m%d)-{{ components }}.md"
```

## 11. Next steps
- id: next_steps
- type: select
- options: ["Implement feature", "Seek more information", "Modify approach", "Consult community forums"]
- prompt: Based on the documentation research, what would you like to do next?

## Notes
- This workflow systematically searches through all local QuantConnect documentation repositories
- It follows the recommended documentation hierarchy: Documentation → lean-cli → Lean → IB Brokerage
- Results are organized into implementation notes for future reference
- The workflow helps identify relevant example algorithms that can serve as templates
- Always verify findings against the current QuantConnect platform version