---
description: Convert a strategy document into a phased implementation plan with human feedback loops for alignment
---

# Strategy to Implementation Plan Workflow

This workflow analyzes a trading strategy document and creates a structured implementation plan with human feedback at key points to ensure alignment.

## 1. Select strategy document
- id: strategy_doc
- type: input
- prompt: Enter the path to the strategy document (.md file):

## 2. Analyze strategy components
```bash
# Display the strategy document for reference
cat "{{ strategy_doc }}"
```

## 3. Identify key components
- id: key_components
- type: input
- prompt: Based on the strategy document, what are the key components that need to be implemented? (comma-separated list)

## 4. Prioritize implementation order
- id: implementation_priority
- type: input
- prompt: What should be the order of implementation priority? Consider technical dependencies and complexity. (comma-separated list)

## 5. Generate draft implementation phases
// This step requires human review before proceeding
- id: draft_phases
- type: multiline
- prompt: Based on the identified components and priorities, here's a draft of implementation phases. Please review and modify as needed:

## 6. Specify implementation details
- id: implementation_details
- type: multiline
- prompt: For each phase, what specific tasks and technical details should be included?

## 7. Create implementation plan document
```bash
# Create implementation plan document
cat > "$(dirname "{{ strategy_doc }}")/$(basename "{{ strategy_doc }}" .md)-implementation-plan.md" << 'EOF'
# Implementation Plan: $(basename "{{ strategy_doc }}" .md | tr '-' ' ' | awk '{for(i=1;i<=NF;i++)sub(/./,toupper(substr($i,1,1)),$i)}1')

## Overview
This document outlines the implementation plan for the [$(basename "{{ strategy_doc }}" .md | tr '-' ' ' | awk '{for(i=1;i<=NF;i++)sub(/./,toupper(substr($i,1,1)),$i)}1') Strategy](./$(basename "{{ strategy_doc }}")).

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

## Testing Criteria

*To be defined for each phase*

## Known Issues and Challenges

*To be updated during implementation*

EOF

echo "Implementation plan created at: $(dirname "{{ strategy_doc }}")/$(basename "{{ strategy_doc }}" .md)-implementation-plan.md"
```

## 8. Review final implementation plan
```bash
# Display the created implementation plan
cat "$(dirname "{{ strategy_doc }}")/$(basename "{{ strategy_doc }}" .md)-implementation-plan.md"
```

## 9. Update strategy document with plan reference (optional)
- id: update_strategy
- type: select
- options: ["Yes", "No"]
- prompt: Would you like to add a reference to the implementation plan in the original strategy document?

## 10. Add reference to strategy document if requested
```bash
if [ "{{ update_strategy }}" = "Yes" ]; then
  # Check if the strategy already has a reference to the implementation plan
  if ! grep -q "Implementation Plan" "{{ strategy_doc }}"; then
    # Add reference to implementation plan
    echo -e "\n## Implementation Plan\n\nA detailed implementation plan is available in [$(basename "{{ strategy_doc }}" .md)-implementation-plan.md](./$(basename "{{ strategy_doc }}" .md)-implementation-plan.md)." >> "{{ strategy_doc }}"
    echo "Added reference to implementation plan in strategy document."
  else
    echo "Strategy document already contains a reference to the implementation plan."
  fi
fi
```

## Notes
- This workflow creates a separate implementation plan document from a strategy document
- Human feedback is incorporated at key points to ensure alignment
- The implementation plan includes phases, technical details, and progress tracking
- The original strategy document can optionally reference the implementation plan
- The implementation plan is created in the same directory as the strategy document
