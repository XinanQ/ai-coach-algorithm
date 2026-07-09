"""AI coach algorithm package.

Loads .env on package import so every entrypoint (uvicorn, eval runs,
offline scripts) sees the same configuration. Real environment variables
always win over .env values (override=False), so shell/-compose settings
are never silently replaced. Without this, local runs only picked up
DEEPSEEK_API_KEY etc. when the shell exported them manually — which made
eval silently fall back to the rule scorer.
"""
try:
    from dotenv import load_dotenv

    load_dotenv(override=False)
except ImportError:  # python-dotenv not installed — keep working, env-only
    pass
