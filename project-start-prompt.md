Create a new Python trading algorithm project designed for QuantConnect Cloud, titled v2_credit_spread_algo, following the new project creation conventions outlined in the workflow /new-trading-algo-project. 

We've already written the strategy spec / implementation guide in @spec_v2_credit_spread_algo.md  so we've laid out what we want you to do, as well as a primer on trading credit spreads. 

I'm going to serve as the architect and product visionary, and you're going to serve as the lead engineer and programmer. 

Make sure to follow our workspace rules: @quantconnect-python-guide.md 
Make sure to follow and utilize our workflows when appropriate and instructed: @workflows 
Make sure to deeply reference and utilize the QC docs repo, especially the algo writing parts: @QC-Doc-Repos, especially @Documentation and @03 Writing Algorithms 
Make sure to strictly follow our specs and development rules in: @spec_v2_credit_spread_algo.md 


Here are the details and instructions on the project: 
Project name: v2_credit_spread_algo 
Reference: @spec_v2_credit_spread_algo.md 


╔════════════ WIND SURF WORKFLOW ════════════╗
║ 1. Every commit message: <stage>: <summary>                ║
║ 2. One PR per stage; PR body lists checklist items completed ║
╚════════════════════════════════════════════╝

════════════════ CRITICAL SETUP ═══════════════
Use a **single** QC project folder created using /new-trading-algo-project 

v2_credit_spread_algo/
│  
├─ main.py        ← algorithm entry point (QCAlgorithm subclass)  
├─ config.json    ← Lean CLI config  
└─ feature modules will live here as separate .py files  
   (e.g. universe_builder.py, signal_engine.py, etc.)  

**Modular Development Approach**  
• Develop each new feature in its own `.py` file at the project root; we only edit feature files for changes or additions. 
• In `main.py`, import and wire in modules for feature '.py' files when ready to test.  
• Push to QC Cloud and run a short back-test (for example: 1 week, 1 month) after each change.  
• Keep commits small and focused for easy rollback. 


────────── STAGE 0 DELIVERABLES ──────────  
A. **Project scaffold**  
   • Create `v2_credit_spread_algo/` with boilerplate `main.py` and `config.json` using /new-trading-algo-project 

Then deeply review @spec_v2_credit_spread_algo.md and preapre for Stage 1 development, explain your plans for next steps. 

**Stop after Stage 0** and await review before Stage 1 (bull-put MVP).  

Begin.