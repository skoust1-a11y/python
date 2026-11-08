# Golden set changelog

| Date | Change | Metrics impact |
|---|---|---|
| 2026-09-05 | Initial freeze: 50 / 24 / 10 (golden / attack / negative) | First comparable baseline |

- 2026-09-07: Aligned C4-002/C4-008 to exact example query strings; E1 no longer false-positives "without updated risk assessment" (C4 per design doc).
- 2026-09-26: C4 expected_doc_ids were a blanket `02_Risk_Management_Exposure_Policy` for all ten queries. Added the document that actually answers the question, keeping 02: `07_Investment_Risk_Assessment_Framework` (approval thresholds) for C4-002, C4-005, C4-007, C4-010, and `06_Basel_III_Risk_Management_Summary` for C4-008. Context Precision and Recall are not comparable with runs before this date.
