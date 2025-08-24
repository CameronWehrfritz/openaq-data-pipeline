# Development Log - OpenAQ Data Pipeline

This development log documents my design and debugging process for the OpenAQ pipeline. I’ve structured it with session-based notes to demonstrate my systematic approach to building production-grade data pipelines — something I expect to discuss in depth during interviews.

Author: Cameron Wehrfritz   
Created: 2025-08-23     
Updated: 2025-08-23 

---

# Session 1: Environment setup and BigQuery connectivity testing
2025-08-23 (5pm-7pm)

- Clean virtual environment setup
- BigQuery connectivity verified
- Sensors table created with proper primary key structure
- Pipeline tested and working (59 sensors inserted)
- Dependencies updated and documented
- Tested duplicate prevention logic → failed, needs revision

## Technical Progress

- Created and activated a new virtual environment (openaq_env)
- Installed required dependencies (google-cloud-bigquery, pandas, requests, python-dotenv)
- Configured .env file for storing GCP project credentials
- Built schema for pm25_ca_sensors with sensor_id as primary key
- Verified BigQuery client connection with test query
- Implemented initial pipeline to pull PM2.5 sensor metadata from OpenAQ API
- Successfully inserted 59 unique CA sensors into BigQuery table

## Problem-Solving Documentation

**Problem:** Duplicate prevention logic failed — repeated API calls inserted duplicate rows.

**Attempted Approach:** Compared incoming records directly against BigQuery table on sensor_id.

**Why It Failed:**

- Datatype mismatch between API payload (string IDs) and BigQuery column (integer IDs).

- Inconsistent timestamp formatting caused false negatives in comparison.
- Next Step:
    - Normalize sensor_id datatype before comparison.
    - Standardize timestamps (ISO 8601 → UTC).
    - Re-test with updated logic.

## Interview Preparation Notes

- Be prepared to explain how to:
    - Enforce primary key integrity when BigQuery doesn’t natively support PK constraints.
    - Handle deduplication when API and DB formats don’t align.
    - Design logging around insert vs skip decisions (important for auditability).
- Anticipate discussion on streaming buffer conflicts when updating BigQuery with multiple jobs.

## Learning Milestones

- First successful end-to-end pipeline test into BigQuery.
- Gained deeper understanding of BigQuery’s limitations (e.g., lack of enforced PKs).
- Identified early need for robust logging and schema validation.

## Time Management

- 2 hours focused on environment setup and connectivity validation.
- Balanced setup tasks with functional testing — avoided over-prepping before validating core pipeline.
- Next session will allocate majority of time to debugging and core class consolidation.

## Session Summary
- **Key Accomplishments:** Environment configured, dependencies documented, BigQuery client verified, sensors table created, and first dataset inserted.
- **Blockers Identified:** Duplicate prevention logic failed due to datatype and timestamp mismatches.
- **Next Session Goals:**
    1. Fix duplicate prevention logic.
    2. Address BigQuery streaming buffer conflict for job tracking updates.

---

# Session 2: Core class consolidation and OOP implementation
2025-08-24 (8am-12pm)

## Technical Progress

## Problem-Solving Documentation

## Interview Preparation Notes

## Learning Milestones

## Time Management

## Session Summary
- **Key Accomplishments:** What major components were completed
- **Blockers Identified:** What needs attention next session
- **Next Session Goals:** Clear objectives for the following work period

---

# Session 3: Core class consolidation and OOP implementation
2025-08-24 (2pm-5pm)

## Technical Progress

## Problem-Solving Documentation

## Interview Preparation Notes

## Learning Milestones

## Time Management

## Session Summary
- **Key Accomplishments:** What major components were completed
- **Blockers Identified:** What needs attention next session
- **Next Session Goals:** Clear objectives for the following work period

---

# Session 4: Integration testing and error handling
2025-08-25 (8am-12pm)

## Technical Progress

## Problem-Solving Documentation

## Interview Preparation Notes

## Learning Milestones

## Time Management

## Session Summary
- **Key Accomplishments:** What major components were completed
- **Blockers Identified:** What needs attention next session
- **Next Session Goals:** Clear objectives for the following work period

---

# Session 5: Final optimization and documentation cleanup
2025-08-25 (2pm-5pm)

## Technical Progress

## Problem-Solving Documentation

## Interview Preparation Notes

## Learning Milestones

## Time Management

## Session Summary
- **Key Accomplishments:** What major components were completed
- **Blockers Identified:** What needs attention next session
- **Next Session Goals:** Clear objectives for the following work period

---