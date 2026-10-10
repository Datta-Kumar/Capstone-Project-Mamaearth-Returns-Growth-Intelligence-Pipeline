import os
import json
from pathlib import Path
from datetime import datetime

from google import genai
from google.genai import types



def generate_scr_narrative(findings: dict) -> dict:
    """Generate a business narrative from verified findings using Gemini."""

    system_instruction = """
You are a senior data analyst writing for Mamaearth's regional
operations and finance heads.

Write the business narrative using exactly these three labeled sections:

Situation
Complication
Resolution

Use only the findings supplied by the user.

Every number in the narrative must come directly from the supplied
findings. Do not invent, estimate, calculate, or introduce any new
statistics.

Keep the narrative business-focused, clear, and actionable.
"""

    user_prompt = f"""
Using the verified findings below, write a concise business narrative
for Mamaearth.

Verified findings:
{json.dumps(findings, indent=2)}

Explain what the data says about returns, revenue quality, the
highest-risk customer segment, and the revenue peak.

Follow the required Situation, Complication, and Resolution structure.
"""

    try:
        client = genai.Client()

        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,

                # Temperature 0.0 keeps this factual report deterministic.
                temperature=0.0,

                # Explicitly set output length as required by the brief.
                max_output_tokens=500,

                # Timeout is 30 seconds (30000 milliseconds).
                http_options=types.HttpOptions(timeout=30000)
            )
        )

        tokens = None

        if response.usage_metadata is not None:
            tokens = response.usage_metadata.total_token_count

        return {
            "status": "success",
            "narrative": response.text,
            "tokens": tokens
        }

    except Exception as err:
        return {
            "status": "error",
            "narrative": None,
            "message": str(err)
        }


def generate_scr_narrative_offline(findings: dict) -> dict:
    """Generate a deterministic SCR narrative without Gemini."""

    peak_month = datetime.strptime(
    findings["true_peak_month"]["month"],
    "%Y-%m"
).strftime("%B %Y")

    return {
        "status": "success",
        "narrative": f"""
Situation

Mamaearth generated ₹{findings["cleaned_total_revenue_inr"]:,.2f}
in cleaned revenue. The analysis shows that COD orders have a
{findings["return_rate_by_payment"]["COD"]:.1f}%
return rate, much higher than the other payment methods.

Complication

The highest-risk segment is {findings["highest_risk_segment"]["payment_method"]}
orders in Tier-{findings["highest_risk_segment"]["city_tier"]}, with a
{findings["highest_risk_segment"]["return_rate_pct"]:.1f}%
return rate. The raw SQL revenue of
₹{findings["raw_total_revenue_inr"]:,.2f} was ₹{findings["duplicate_reconciliation_delta_inr"]:,.2f}
higher than the cleaned revenue because of duplicate orders.

The apparent revenue peak in
{findings["outlier_inflated_month"]["month"]} was
₹{findings["outlier_inflated_month"]["apparent_revenue_inr"]:,.2f},
but after removing the quantity outliers, January's revenue was corrected to
₹{findings["outlier_inflated_month"]["corrected_revenue_inr"]:,.2f}.

Resolution

Operations should prioritize the COD + Tier-2 segment for return
reduction and ensure duplicate orders are controlled in the reporting
pipeline. The true revenue peak was
{peak_month} ({findings["true_peak_month"]["revenue_inr"]:,.2f}).
This corrected view provides a more reliable basis for operational
and financial decisions.
""".strip(),
        "tokens": None
    }

def check_narrative_numbers(narrative: str) -> bool:
    """Check that all required verified figures appear in the narrative."""

    normalized = narrative.replace(",", "")

    checks = {
        "Cleaned revenue 97,358.30": "97358.30" in normalized
        or "97358.3" in normalized,

        "COD return rate 44.4": "44.4" in normalized,

        "COD + Tier-2 return rate 54.5": "54.5" in normalized,

        "Duplicate reconciliation delta 2,501.90": "2501.90" in normalized
        or "2501.9" in normalized,

        "March peak revenue 20,318.90": (
            "march" in narrative.lower()
            and ("20318.90" in normalized or "20318.9" in normalized)
        )
    }

    all_passed = True

    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")
        assert passed, f"Numeric accuracy check failed: {name}"

    print("\nNumeric accuracy check: PASS")

    return True




if __name__ == "__main__":
    project_dir = Path(__file__).resolve().parent.parent
    narrator_dir = project_dir / "narrator"
    findings_path = narrator_dir / "findings.json"
    sample_path = narrator_dir / "sample_output.txt"

    with open(findings_path, "r", encoding="utf-8") as f:
        findings = json.load(f)

    api_key = os.getenv("GEMINI_API_KEY")
    online_success = False

    if api_key:
        result = generate_scr_narrative(findings)

        if result["status"] == "error":
            print("Gemini API failed.")
            print("Error:", result["message"])
            print("Using offline fallback.")
            result = generate_scr_narrative_offline(findings)
        else:
            online_success = True
    else:
        print("No GEMINI_API_KEY found. Using offline fallback.")
        result = generate_scr_narrative_offline(findings)

    narrative = result["narrative"]
    print("\n" + narrative)

    if online_success:
        sample_path.write_text(
            narrative.strip() + "\n",
            encoding="utf-8"
        )
        print("\nSaved successful Gemini output to sample_output.txt")

        # Check the saved sample, as required by the project brief.
        saved_narrative = sample_path.read_text(encoding="utf-8")
        check_narrative_numbers(saved_narrative)
    else:
        # Keep the existing successful Gemini sample unchanged.
        check_narrative_numbers(narrative)
