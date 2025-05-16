---
description: Converts a Python algorithm component into a Jupyter Notebook for testing on QuantConnect Cloud, then pushes the project.
---

# Workflow: Convert Python Component to QuantConnect Research Notebook

---
description: Converts a Python algorithm component into a Jupyter Notebook for testing on QuantConnect Cloud, then pushes the project.
---

## Steps

*(To be defined after walking through a practical example.)*

1.  Identify the Python component file (e.g., `my_component.py`).
2.  Create a new Jupyter Notebook (e.g., `research_my_component.ipynb`) or select an existing one.
3.  Adapt/copy the component's code into notebook cells.
    *   Include necessary `QuantBook` initializations.
    *   Set up mock data or fetch minimal historical data required for the component.
    *   Add cells to execute the component's logic and print/plot results.
4.  Ensure the project is configured for QuantConnect Cloud.
5.  Use Lean CLI to push the project (including the new/updated notebook) to QuantConnect Cloud: `lean cloud push --project "YourProjectName"`.
6.  Open the notebook on the QuantConnect Cloud platform to run and verify the component.
