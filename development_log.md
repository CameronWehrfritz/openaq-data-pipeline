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

### BigQuery Schema Design
**Table:** pm25_ca_sensors  
**Primary Key:** sensor_id (STRING, REQUIRED)  
**Key Fields:** location_id, lat/lon (REQUIRED), timestamps (datetimeFirst/Last, created_at, updated_at)  
**Total Columns:** 20 fields covering sensor metadata, location data, ownership, and audit trails  
**Notable Decisions:** 
- sensor_id as STRING (not INTEGER) to match OpenAQ API format
- Separate created_at/updated_at for audit tracking
- Nullable fields for optional OpenAQ metadata

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

# Session 2: Schema fixes and BigQuery streaming buffer debugging
2025-08-24 (8:10am-10:15am)

## Technical Progress

- **Schema correction:** Changed sensor_id from STRING to INTEGER based on OpenAQ API documentation
- **Table recreation:** Dropped and recreated pm25_ca_sensors table with correct schema
- **Duplicate prevention verified:** Second pipeline run correctly identified 0 new sensors
- **Update mechanism implemented** Added MERGE-based update logic for existing sensor records
- **Streaming buffer workaround:** Modified pipeline to skip updates when new data is inserted

## Problem-Solving Documentation

**Primary Problem:** Duplicate prevention logic failed - repeated API calls inserted duplicate rows     
**Root Cause:** Schema mismatch (sensor_id STRING vs INTEGER)      
**Solution:** Schema correction and table recreation

**Debugging Process:**
- Added debug logging to trace boolean values through data pipeline
- Confirmed API returns proper Python bool types (True/False)
- Tested explicit bool() conversion - no improvement
- Issue persists despite correct data types in parameters
- Tested MERGE vs UPDATE query approaches
- **Actual Root Cause:** BigQuery streaming buffer limitations prevent updates on recently inserted data
- **Solution:** Logic change to skip updates when new insertions occur, avoiding streaming buffer conflicts

**Secondary Problem:** Update operations failing due to Boolean Parameter Binding (Unresolved)
- Error: "Invalid value for type: BOOLEAN is not a valid value"
- Occurs in MERGE operations regardless of streaming buffer status
- INSERT behavior with boolean fields not yet verified in current setup
- Current workaround: Exclude boolean fields from updates
- Root cause hypothesis: BigQuery parameter binding issue with boolean fields, cause unknown

### Performance Observation:

- Individual sensor updates via MERGE: ~2 minutes for 22 sensors (~5.5 seconds per sensor)
- Indicates need for batch update optimization in future iterations

## Performance Metrics

- API response time: 1.6-5.5 seconds for 59 sensors
- Successfully processed sensor updates in ~2 minutes
- Update success rate: 100% after streaming buffer fix

## Learning Milestones

- BigQuery streaming buffer behavior impacts UPDATE/DELETE operations on recently inserted data
- Misleading error messages can mask underlying infrastructure limitations
- Systematic debugging with targeted logging reveals true root causes
- Schema validation against API documentation prevents integration issues

## Session Summary

- **Key Accomplishments:** Fixed duplicate prevention, implemented working update mechanism, resolved streaming buffer conflicts
- **Blockers Resolved:** Schema datatype mismatch, BigQuery streaming buffer limitations
- **Next Session Goals:** batch update optimization for sensors

**Technical Debt:** Boolean fields excluded from updates pending resolution of BigQuery MERGE parameter issue

---

# Session 3: Core class consolidation and OOP implementation
2025-08-24 (10:30am-12pm)

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