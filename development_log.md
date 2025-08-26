# Development Log - OpenAQ Data Pipeline

This development log documents my design and debugging process for the OpenAQ pipeline. I’ve structured it with session-based notes to demonstrate my systematic approach to building production-grade data pipelines — something I expect to discuss in depth during interviews.

Author: Cameron Wehrfritz   
Created: 2025-08-23     
Updated: 2025-08-25

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
2025-08-24 (8:10am-10:40am)

## 1. Technical Progress

- **Schema correction:** Changed sensor_id from STRING to INTEGER based on OpenAQ API documentation
- **Table recreation:** Dropped and recreated pm25_ca_sensors table with correct schema
- **Duplicate prevention verified:** Second pipeline run (fresh API call) correctly identified 0 new sensors
- **Update mechanism implemented** Added MERGE-based update logic for existing sensor records
- **Streaming buffer workaround:** Modified pipeline to skip updates when new data is inserted

## 2. Problem-Solving Documentation

### 2.1 Primary Issue: Duplicate Prevention Logic

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

### 2.2 Secondary Issue: Boolean Parameter Binding (Unresolved)

**Secondary Problem:** Update operations failing due to Boolean Parameter Binding
- Error: "Invalid value for type: BOOLEAN is not a valid value"
- Occurs in MERGE operations regardless of streaming buffer status
- INSERT behavior with boolean fields not yet verified in current setup
- Current workaround: Exclude boolean fields from updates
- Root cause hypothesis: BigQuery parameter binding issue with boolean fields, cause unknown

### 2.3 Performance Observation

- Individual sensor updates via MERGE: ~2 minutes for 22 sensors (~5.5 seconds per sensor)
- Indicates need for batch update optimization in future iterations

## 3. Performance Metrics

- API response time: 1.6-5.5 seconds (59 sensors)
- Individual sensor updates: ~5.5 seconds per sensor (22 sensors total)
- Overall update duration: ~2 minutes
- Update success rate: 100% (post-streaming buffer fix)

## 4. Learning Milestones

- BigQuery streaming buffer behavior impacts UPDATE/DELETE operations on recently inserted data
- Misleading error messages can mask underlying infrastructure limitations
- Systematic debugging with targeted logging reveals true root causes
- Schema validation against API documentation prevents integration issues

## 5. Time Management

- First 2 hours was very focused, final half hour was less efficient
- Next session, take 20 minute walk break between 90-120 minute mark to ensure efficiency

## 6. Session Summary

- **Key Accomplishments:** Fixed duplicate prevention, implemented working update mechanism, resolved streaming buffer conflicts
- **Blockers Resolved:** Schema datatype mismatch, BigQuery streaming buffer limitations
- **Next Session Goals:** Investigate bulk MERGE operations

**Technical Debt:** Boolean fields excluded from updates pending resolution of BigQuery MERGE parameter issue

---

# Session 3: Investigate bulk MERGE operations
2025-08-24 (1:35pm-2:45pm)

## 1. Technical Progress

**Technical Solution:**
- Temporary table + MERGE approach instead of STRUCT array parameters     
- Single database round-trip vs 23 individual MERGE operations    
- Automatic cleanup of temporary tables  

## 2. Problem-Solving Documentation

**Primary Problem:** Initial bulk MERGE implementation using STRUCT array parameters failed with BigQuery error

```
Invalid value for type: STRUCT<sensor_id INT64, location_name STRING, locality STRING, lat FLOAT64, lon FLOAT64, datetimeFirst TIMESTAMP, datetimeLast TIMESTAMP, updated_at TIMESTAMP> is not a valid value
```

**Root Cause Analysis:**

- BigQuery's ArrayQueryParameter with complex STRUCT types has strict formatting requirements
- Python object-to-BigQuery type conversion failed, likely due to timestamp formatting or null value handling
- STRUCT array approach works well for simple data types but becomes unreliable with mixed nulls, timestamps, and floating-point precision

**Solution Discovery Process:**

1. Initial approach: UNNEST with STRUCT array - failed due to parameter binding issues
2. Debugging attempt: Examined data types and null handling - error persisted
3. Alternative evaluation: Considered temporary table approach as more reliable method
4. Implementation: Temporary table + MERGE pattern with explicit schema definition

**Why Temporary Table Approach Worked:**

- Explicit schema control: Temporary table schema matches target table exactly
- Standard INSERT operations: Avoids complex parameter binding entirely
- Reliable type conversion: BigQuery handles data type conversion during INSERT
- Proven pattern: Temporary table + MERGE is a well-established BigQuery bulk operation pattern
- Error isolation: Failures occur at predictable points (table creation, data insertion, or MERGE execution)

**Technical Implementation:**

- UUID-based temporary table naming prevents concurrent execution conflicts
    - If multiple pipeline instances run simultaneously - each gets a unique table name
    - Without this, two concurrent runs could try creating the same temp table and fail
- Automatic cleanup with error handling ensures no orphaned tables
- Graceful fallback to individual updates maintains pipeline reliability

## 3. Performance Metrics

### 3.1 Bulk Update
- Before: Individual MERGE operations (~5.5 seconds per sensor × 23 sensors = ~120 seconds)
- After: Single bulk operation (4.73 seconds)
- Method: Temporary table creation → data insertion → MERGE → cleanup

### 3.2 Entire Pipeline
- Total pipeline execution time 13 seconds
- Overall performance improvement (~25x faster for updates)

## 4. Learning Milestones

- When to choose temporary tables vs STRUCT arrays: temp tables better for 100+ rows, complex data types, or reliability over slight performance gains
- The temporary table approach trades slight overhead (table creation/deletion) for significantly improved reliability and debuggability
- Fallback strategy implementation (graceful degradation to individual updates)
- Python provides a built-in uuid module for generating Universally Unique Identifiers (UUIDs), also known as Globally Unique Identifiers (GUIDs). UUIDs are 128-bit numbers used to uniquely identify information in distributed systems, minimizing the chance of identifier collisions.

## 5. Time Management

- Efficient 80-minute optimization session delivered 25x performance improvement

## 6. Session Summary

- **Key Accomplishments:** Bulk update with BigQuery temporary table
- **Blockers Identified:** None
- **Next Session Goals:** Explore error handling improvements, data validation and monitoring capabilities

**Technical Debt:** Boolean fields excluded from updates pending resolution of BigQuery MERGE parameter issue

---

# Session 4: Consolidate core functionality into a single consolidated script for interview
2025-08-25 (8am-12pm)

## 1. Technical Progress

- Consolidated core functionality from class-based version into a single script for interview
- Focused on core data engineering concepts and readability

## 2. Time Management

- Efficient extended 4-hour session
- Split session with 30-minute walking break; helped maintain focus in second half of session

## 3. Session Summary

- **Key Accomplishments:** Consolidated core functionality into a single script
- **Blockers Identified:** Timestamp comparison causing false positive updates
- **Next Session Goals:** 
  1. Fix timestamp comparison causing false positive updates
  2. Add additional features:
    - API rate limiting
    - NULL value reporting
    - row count validation and monitoring

---

# Session 5: Implement final features for interview demo
2025-08-25 (2:30pm-5pm)

## 1. Technical Progress

### 1.1 Fixed false positives in timestamp comparison

- Normalized both API and database timestamps to ISO format before
comparison
- Eliminated unnecessary bulk updates when data unchanged

### 1.2 Improved pipeline robustness and data quality monitoring
- Implemented API rate limiting to ensure compliance with OpenAQ API usage policies and prevent request failures
- Added NULL value reporting for improved data quality monitoring and debugging
- Introduced row count validation and monitoring to track ingestion consistency and detect pipeline anomalies

## 2. Problem-Solving Documentation

- Resolved timestamp mismatch issue by identifying format discrepancies between API and BigQuery
- Decided to use ISO normalization instead of schema changes to maintain compatibility with existing tables

## 3. Performance Metrics

- Confirmed pipeline ingests ~59 sensors in <5s with rate-limiting enabled
- Validated row counts remain consistent across test runs

## 4. Learning Milestones

- Gained deeper understanding of practical API rate-limiting strategies.
- Strengthened skills in logging and monitoring for data pipelines (standard logging levels in Python's built in logging module: DEBUG, INFO, WARNING, ERROR, CRITICAL)


## 5. Time Management

- Efficient 2.5-hour session
- Allocated ~1 hour to debugging timestamp mismatch
- Spent ~1.5 hours implementing and testing robustness features
- Reserved final 30 min for documentation and commit preparation

## 6. Session Summary

- **Key Accomplishments:**
  1. Fix timestamp comparison causing false positive updates
  2. Implemented API rate limiting, NULL value reporting and row count validation and monitoring
- **Blockers Identified:** None
- **Next Session Goals:** Add explanatory comments for interview walkthrough

---