---
description: Convert a trading strategy document into a phased implementation plan with human feedback loops for alignment
---

# WARNING: DO NOT MODIFY THIS FILE WITHOUT EXPLICIT USER PERMISSION
# Trading Strategy to Implementation Plan Workflow

This workflow analyzes a QuantConnect trading strategy document and creates a structured implementation plan with human feedback at key points to ensure alignment.

## 1. Select trading strategy document
- id: strategy_doc
- type: input
- prompt: Enter the path to the trading strategy document (.md file):

## 2. Analyze trading strategy components
```bash
# Display the trading strategy document for reference
cat "{{ strategy_doc }}"
```

## 3. Identify key trading components
- id: key_components
- type: input
- prompt: Based on the trading strategy document, what are the key components that need to be implemented? (e.g., option chain filtering, spread construction, entry/exit signals)

## 4. Prioritize implementation order
- id: implementation_priority
- type: input
- prompt: What should be the order of implementation priority? Consider technical dependencies, QuantConnect-specific requirements, and trading complexity.

## 5. Generate draft implementation phases
// This step requires human review before proceeding
- id: draft_phases
- type: multiline
- prompt: Based on the identified components and priorities, here's a draft of implementation phases for the trading algorithm. Please review and modify as needed:

## 6. Research documentation for implementation details
```bash
echo "Researching QuantConnect documentation for implementation guidance..."
echo "============================================================="

# Search in Documentation repository for key components
grep -r --include="*.md" --include="*.html" --include="*.py" "{{ key_components }}" /Users/overton/CascadeProjects/QuantConnect\ Trading\ Algorithms/.windsurf/QC-Doc-Repos/Documentation | head -n 10

# Search in lean-cli repository for deployment information
grep -r --include="*.md" --include="*.py" "{{ key_components }}" /Users/overton/CascadeProjects/QuantConnect\ Trading\ Algorithms/.windsurf/QC-Doc-Repos/lean-cli | head -n 5

# Find example algorithms in Lean repository
find /Users/overton/CascadeProjects/QuantConnect\ Trading\ Algorithms/.windsurf/QC-Doc-Repos/Lean/Algorithm.Python -type f -name "*{{ key_components }}*.py" | head -n 5
```

## 7. Specify implementation details based on documentation
- id: implementation_details
- type: multiline
- prompt: Based on the documentation search results, what specific trading tasks, QuantConnect API calls, and technical details should be included for each phase?

## 8. Create implementation plan document
```bash
# Create implementation plan document
cat > "$(dirname "{{ strategy_doc }}")/$(basename "{{ strategy_doc }}" .md)-implementation-plan.md" << 'EOF'
# Implementation Plan: $(basename "{{ strategy_doc }}" .md | tr '-' ' ' | awk '{for(i=1;i<=NF;i++)sub(/./,toupper(substr($i,1,1)),$i)}1')

## Overview
This document outlines the implementation plan for the [$(basename "{{ strategy_doc }}" .md | tr '-' ' ' | awk '{for(i=1;i<=NF;i++)sub(/./,toupper(substr($i,1,1)),$i)}1') Trading Strategy](./$(basename "{{ strategy_doc }}")).

## Implementation Phases

{{ draft_phases }}

## Technical Implementation Details

{{ implementation_details }}

## Progress Tracking

| Phase | Status | Notes | Completed Date |
|-------|--------|-------|----------------|
| Phase 1 | Not Started | | |
| Phase 2 | Not Started | | |
| Phase 3 | Not Started | | |
| Phase 4 | Not Started | | |
| Phase 5 | Not Started | | |
| Phase 6 | Not Started | | |

## Backtesting Criteria

| Phase | Test Period | Success Metrics | Status |
|-------|-------------|----------------|--------|
| Phase 1 | | | Not Tested |
| Phase 2 | | | Not Tested |
| Phase 3 | | | Not Tested |
| Phase 4 | | | Not Tested |
| Phase 5 | | | Not Tested |
| Phase 6 | | | Not Tested |

## QuantConnect-Specific Considerations

*Document any platform-specific implementation details, limitations, or workarounds based on the documentation research*

## Documentation References

- Documentation Repository: `.windsurf/QC-Doc-Repos/Documentation`
- Lean CLI Repository: `.windsurf/QC-Doc-Repos/lean-cli`
- Lean Engine Repository: `.windsurf/QC-Doc-Repos/Lean`
- Example Algorithms: `.windsurf/QC-Doc-Repos/Lean/Algorithm.Python`

## Known Issues and Challenges

*To be updated during implementation*

EOF

echo "Trading algorithm implementation plan created at: $(dirname "{{ strategy_doc }}")/$(basename "{{ strategy_doc }}" .md)-implementation-plan.md"
```

## 9. Review final implementation plan
```bash
# Display the created implementation plan
cat "$(dirname "{{ strategy_doc }}")/$(basename "{{ strategy_doc }}" .md)-implementation-plan.md"
```

## 10. Update strategy document with plan reference (optional)
- id: update_strategy
- type: select
- options: ["Yes", "No"]
- prompt: Would you like to add a reference to the implementation plan in the original trading strategy document?

## 11. Add reference to strategy document if requested
```bash
if [ "{{ update_strategy }}" = "Yes" ]; then
  # Check if the strategy already has a reference to the implementation plan
  if ! grep -q "Implementation Plan" "{{ strategy_doc }}"; then
    # Add reference to implementation plan
    echo -e "\n## Implementation Plan\n\nA detailed implementation plan for this trading algorithm is available in [$(basename "{{ strategy_doc }}" .md)-implementation-plan.md](./$(basename "{{ strategy_doc }}" .md)-implementation-plan.md)." >> "{{ strategy_doc }}"
    echo "Added reference to implementation plan in trading strategy document."
  else
    echo "Trading strategy document already contains a reference to the implementation plan."
  fi
fi
```

## Notes
- This workflow creates a separate implementation plan document from a trading strategy document
- Human feedback is incorporated at key points to ensure alignment
- The implementation plan includes phases, QuantConnect-specific technical details, and progress tracking
- Backtesting criteria are included for each phase to validate implementation
- Documentation research is automatically performed to guide implementation details
- **IMPORTANT**: All Python code must use snake_case for method names (e.g., `initialize` not `Initialize`)
- The original trading strategy document can optionally reference the implementation plan
- The implementation plan is created in the same directory as the trading strategy document