"""
Session state key constants for the SyncWatt ADK pipeline.

Data flow:
  image_bytes -> VisionAgent -> raw_text
  raw_text -> OcrRefinerAgent -> settlement_data
  image_bytes -> DirectVisionAgent -> visual_data
  settlement_data + visual_data -> CodeVerifierAgent -> settlement_data (verified)
  settlement_data -> DataFetcherAgent -> market_data
  settlement_data + market_data -> DiagnosisCalculatorAgent -> diagnosis_calc
  diagnosis_calc -> DiagnosisAgent -> analysis_result
"""

# Pipeline input
IMAGE_BYTES = "image_bytes"

# OCR path
RAW_TEXT = "raw_text"
SETTLEMENT_DATA = "settlement_data"

# Vision path
VISUAL_DATA = "visual_data"

# Market data
MARKET_DATA = "market_data"

# Diagnosis
DIAGNOSIS_CALC = "diagnosis_calc"
CAUSE = "cause"
IRR_DIFF_PCT = "irr_diff_pct"
SMP_DIFF_PCT = "smp_diff_pct"

# Final output
ANALYSIS_RESULT = "analysis_result"
