"""
NYC 311 ETL - Simple Procedural Version (No Classes/Functions)
================================================================
A straightforward, script-based ETL that's easy to understand and modify.
No complex OOP - just straightforward code from top to bottom.
"""

import requests
import mysql.connector
import logging
from datetime import datetime
import time

# =============================================================================
# CONFIGURATION (Edit these values)
# =============================================================================

# API Settings
API_URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
API_TOKEN = None  # Optional: Get from https://data.cityofnewyork.us/profile/app_tokens
BATCH_SIZE = 1000  # How many records to fetch per API call
MAX_RECORDS = 1000  # Maximum records to load (10,000 = ~2 weeks of data)

# Database Settings
DB_HOST = "nyc311.mysql.database.azure.com"
DB_PORT = 3306
DB_DATABASE = "nyc311_dw"
DB_USER = "michaelha"
DB_PASSWORD = "team1@USD"
DB_SSL = True   # Azure MySQL requires SSL

# ETL Settings
# Checkpoint is now stored in the etl_checkpoint table in the database
DB_BATCH_SIZE = 500  # How many records to insert at once

# Logging Settings
LOG_FILE = "etl.log" # change it to github link if you want to store it in github repo instead of local file system
LOG_LEVEL = logging.INFO

# =============================================================================
# SETUP LOGGING
# =============================================================================

logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logging.info("=" * 80)
logging.info("Starting NYC 311 ETL Process")
logging.info("=" * 80)

# =============================================================================
# LOAD CHECKPOINT FROM DATABASE (for incremental loading)
# =============================================================================

last_timestamp = None
# Note: Database connection happens after this section, so we'll load checkpoint
# after connecting to the database (moved below)

# =============================================================================
# CONNECT TO DATABASE
# =============================================================================

logging.info("Connecting to Azure MySQL database...")
db_conn = mysql.connector.connect(
    host=DB_HOST,
    port=DB_PORT,
    database=DB_DATABASE,
    user=DB_USER,
    password=DB_PASSWORD,
    autocommit=False,
    ssl_disabled=not DB_SSL,   # Azure requires SSL
    ssl_verify_cert=False,     # Set True + ssl_ca path for full cert verification
    connection_timeout=60
)
cursor = db_conn.cursor()
logging.info("Azure MySQL database connected")

# Load checkpoint from database
try:
    cursor.execute("""
        SELECT last_extracted_timestamp
        FROM etl_checkpoint
        ORDER BY checkpoint_id DESC
        LIMIT 1
    """)
    result = cursor.fetchone()
    if result and result[0]:
        last_timestamp = result[0].isoformat() if hasattr(result[0], 'isoformat') else str(result[0])
        logging.info(f"Loaded checkpoint from database: Incremental load from {last_timestamp}")
    else:
        logging.info("No checkpoint found in database, performing full load")
except Exception as e:
    logging.warning(f"Could not load checkpoint from database: {e}")
    logging.info("Performing full load")

# Initialize run log entry
etl_run_id = None
try:
    cursor.execute("""
        INSERT INTO etl_run_log (status) VALUES ('running')
    """)
    db_conn.commit()
    etl_run_id = cursor.lastrowid
    logging.info(f"ETL run started, run_id: {etl_run_id}")
except Exception as e:
    logging.warning(f"Could not create run log entry: {e}")

# =============================================================================
# STATISTICS
# =============================================================================

total_extracted = 0
total_loaded = 0
total_errors = 0

# =============================================================================
# MAIN ETL LOOP
# =============================================================================

offset = 0
latest_created_date = None

# In-memory caches for dimension lookups (avoids repeated DB round-trips)
status_cache = {}   # status_name -> status_id
channel_cache = {}  # channel_type -> channel_id
agency_cache = {}   # agency_code -> agency_id
problem_cache = {}  # (problem_type, problem_detail) -> problem_id

try:
    while True:
        # Check if we've hit the limit
        if MAX_RECORDS and total_extracted >= MAX_RECORDS:
            logging.info(f"Reached MAX_RECORDS limit: {MAX_RECORDS}")
            break

        # ---------------------------------------------------------------------
        # EXTRACT: Fetch batch from API
        # ---------------------------------------------------------------------

        logging.info(f"Fetching batch at offset {offset}...")

        # Build API parameters
        params = {
            '$limit': BATCH_SIZE,
            '$offset': offset,
            '$order': 'created_date ASC'
        }

        # Add filter if we have a checkpoint (for incremental loads after first run)
        if last_timestamp:
            params['$where'] = f"created_date > '{last_timestamp}'"

        # Make API request
        headers = {}
        if API_TOKEN:
            headers['X-App-Token'] = API_TOKEN

        try:
            response = requests.get(API_URL, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            records = response.json()
        except Exception as e:
            logging.error(f"API request failed: {e}")
            # Retry once after 5 seconds
            time.sleep(5)
            try:
                response = requests.get(API_URL, params=params, headers=headers, timeout=30)
                response.raise_for_status()
                records = response.json()
            except Exception as e2:
                logging.error(f"API request failed again: {e2}")
                break

        # Check if we got any records
        if not records or len(records) == 0:
            logging.info("No more records to fetch")
            break

        num_records = len(records)
        logging.info(f"Fetched {num_records} records")
        total_extracted += num_records

        # ---------------------------------------------------------------------
        # TRANSFORM & LOAD: Process each record
        # ---------------------------------------------------------------------

        batch_for_db = []

        for record in records:
            try:
                # ---------------------------------------------------------
                # TRANSFORM: Extract and clean data
                # ---------------------------------------------------------

                unique_key = int(record.get('unique_key', 0))

                # Parse dates (handle None gracefully)
                def parse_date(date_str):
                    if not date_str:
                        return None
                    try:
                        return datetime.strptime(date_str.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                    except:
                        return None

                created_ts = parse_date(record.get('created_date'))
                closed_ts = parse_date(record.get('closed_date'))
                due_ts = parse_date(record.get('due_date'))
                resolution_ts = parse_date(record.get('resolution_action_updated_date'))

                # Track latest timestamp for checkpoint
                if created_ts and (not latest_created_date or created_ts > latest_created_date):
                    latest_created_date = created_ts

                # Clean strings (truncate and strip)
                def clean_str(value, max_len=None):
                    if not value:
                        return None
                    s = str(value).strip()
                    if not s:
                        return None
                    if max_len and len(s) > max_len:
                        return s[:max_len]
                    return s

                # Extract dimension values
                status_name = clean_str(record.get('status'), 64)
                channel_type = clean_str(record.get('open_data_channel_type'), 64)
                agency_code = clean_str(record.get('agency'), 32)
                agency_name = clean_str(record.get('agency_name'), 255)
                problem_type = clean_str(record.get('complaint_type'), 255)
                problem_detail = clean_str(record.get('descriptor'), 255)

                # Extract location data
                incident_address = clean_str(record.get('incident_address'), 255)
                street_name = clean_str(record.get('street_name'), 255)
                city = clean_str(record.get('city'), 255)
                zip_code = clean_str(record.get('incident_zip'), 20)
                borough = clean_str(record.get('borough'), 64)

                # Parse coordinates
                def parse_float(value):
                    if not value:
                        return None
                    try:
                        return float(value)
                    except:
                        return None

                latitude = parse_float(record.get('latitude'))
                longitude = parse_float(record.get('longitude'))

                # ---------------------------------------------------------
                # LOAD: Insert dimensions and get IDs
                # ---------------------------------------------------------

                # Insert/get status dimension (cached)
                status_id = None
                if status_name:
                    if status_name in status_cache:
                        status_id = status_cache[status_name]
                    else:
                        cursor.execute("INSERT IGNORE INTO dim_status (status_name) VALUES (%s)", (status_name,))
                        cursor.execute("SELECT status_id FROM dim_status WHERE status_name = %s", (status_name,))
                        result = cursor.fetchone()
                        if result:
                            status_id = result[0]
                            status_cache[status_name] = status_id

                # Insert/get channel dimension (cached)
                channel_id = None
                if channel_type:
                    if channel_type in channel_cache:
                        channel_id = channel_cache[channel_type]
                    else:
                        cursor.execute("INSERT IGNORE INTO dim_channel (channel_type) VALUES (%s)", (channel_type,))
                        cursor.execute("SELECT channel_id FROM dim_channel WHERE channel_type = %s", (channel_type,))
                        result = cursor.fetchone()
                        if result:
                            channel_id = result[0]
                            channel_cache[channel_type] = channel_id

                # Insert/get agency dimension (cached)
                agency_id = None
                if agency_code:
                    if agency_code in agency_cache:
                        agency_id = agency_cache[agency_code]
                    else:
                        cursor.execute(
                            "INSERT IGNORE INTO dim_agency (agency_code, agency_name) VALUES (%s, %s)",
                            (agency_code, agency_name)
                        )
                        cursor.execute(
                            "SELECT agency_id FROM dim_agency WHERE agency_code = %s",
                            (agency_code,)
                        )
                        result = cursor.fetchone()
                        if result:
                            agency_id = result[0]
                            agency_cache[agency_code] = agency_id

                # Insert/get problem dimension (cached)
                problem_id = None
                if problem_type:
                    problem_key = (problem_type, problem_detail)
                    if problem_key in problem_cache:
                        problem_id = problem_cache[problem_key]
                    else:
                        cursor.execute(
                            "INSERT IGNORE INTO dim_problem (problem_type, problem_detail) VALUES (%s, %s)",
                            (problem_type, problem_detail)
                        )
                        cursor.execute(
                            "SELECT problem_id FROM dim_problem WHERE problem_type = %s AND (problem_detail = %s OR (problem_detail IS NULL AND %s IS NULL))",
                            (problem_type, problem_detail, problem_detail)
                        )
                        result = cursor.fetchone()
                        if result:
                            problem_id = result[0]
                            problem_cache[problem_key] = problem_id

                # Insert location (simplified - just address and geography)
                location_id = None
                if incident_address or latitude:
                    # Insert address
                    address_id = None
                    if incident_address:
                        cursor.execute(
                            "INSERT INTO dim_address (incident_address, street_name, city, incident_zip, borough, address_type, location_type, facility_type) VALUES (%s, %s, %s, %s, %s, NULL, NULL, NULL)",
                            (incident_address, street_name, city, zip_code, borough)
                        )
                        address_id = cursor.lastrowid

                    # Insert geography
                    geography_id = None
                    if latitude:
                        cursor.execute(
                            "INSERT INTO dim_geography (latitude, longitude, x_coordinate_state_plane, y_coordinate_state_plane, location_text) VALUES (%s, %s, NULL, NULL, NULL)",
                            (latitude, longitude)
                        )
                        geography_id = cursor.lastrowid

                    # Insert location hub
                    if address_id or geography_id:
                        cursor.execute(
                            "INSERT INTO dim_location (address_id, neighborhood_id, park_id, highway_id, taxi_id, geography_id) VALUES (%s, NULL, NULL, NULL, NULL, %s)",
                            (address_id, geography_id)
                        )
                        location_id = cursor.lastrowid

                # Insert fact record
                cursor.execute("""
                    REPLACE INTO fact_service_request (
                        unique_key, created_ts, closed_ts, resolution_action_updated_ts, due_ts,
                        additional_details, resolution_description,
                        status_id, channel_id, agency_id, problem_id, location_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    unique_key, created_ts, closed_ts, resolution_ts, due_ts,
                    problem_detail, clean_str(record.get('resolution_description'), 255),
                    status_id, channel_id, agency_id, problem_id, location_id
                ))

                total_loaded += 1
                if total_loaded % 100 == 0:
                    logging.info(f"Progress: {total_loaded} records loaded so far...")

            except Exception as e:
                logging.error(f"Error processing record {record.get('unique_key')}: {e}")
                total_errors += 1
                continue

        # Commit the batch (ping first to detect/recover dropped connections)
        db_conn.ping(reconnect=True, attempts=3, delay=2)
        db_conn.commit()
        logging.info(f"Batch committed: {len(records)} processed, {total_errors} errors so far")

        # Check if we got a full batch (if not, we're done)
        if num_records < BATCH_SIZE:
            logging.info("Received partial batch, ending extraction")
            break

        # Move to next batch
        offset += BATCH_SIZE
        time.sleep(0.5)  # Rate limiting

except KeyboardInterrupt:
    logging.warning("ETL interrupted by user")
    # Update run log for interruption
    if etl_run_id:
        try:
            cursor.execute("""
                UPDATE etl_run_log
                SET end_time = NOW(),
                    status = 'interrupted',
                    records_extracted = %s,
                    records_loaded = %s,
                    errors_count = %s,
                    error_summary = 'ETL interrupted by user'
                WHERE run_id = %s
            """, (total_extracted, total_loaded, total_errors, etl_run_id))
            db_conn.commit()
        except:
            pass
except Exception as e:
    error_msg = str(e)
    logging.error(f"ETL failed with error: {e}", exc_info=True)
    db_conn.rollback()
    # Update run log for failure
    if etl_run_id:
        try:
            cursor.execute("""
                UPDATE etl_run_log
                SET end_time = NOW(),
                    status = 'failed',
                    records_extracted = %s,
                    records_loaded = %s,
                    errors_count = %s,
                    error_summary = %s
                WHERE run_id = %s
            """, (total_extracted, total_loaded, total_errors, error_msg[:1000], etl_run_id))
            db_conn.commit()
        except:
            pass
finally:
    # =============================================================================
    # CLEANUP & SAVE CHECKPOINT TO DATABASE
    # =============================================================================

    # Save checkpoint to database
    if latest_created_date:
        try:
            cursor.execute("""
                INSERT INTO etl_checkpoint (
                    last_extracted_timestamp,
                    records_loaded,
                    etl_status
                ) VALUES (%s, %s, %s)
            """, (latest_created_date, total_loaded, 'completed'))
            db_conn.commit()
            logging.info(f"Checkpoint saved to database: last_timestamp={latest_created_date.isoformat()}, records={total_loaded}")
        except Exception as e:
            logging.error(f"Failed to save checkpoint to database: {e}")

    # Update run log with final statistics
    if etl_run_id:
        try:
            cursor.execute("""
                UPDATE etl_run_log
                SET end_time = NOW(),
                    status = 'completed',
                    records_extracted = %s,
                    records_loaded = %s,
                    errors_count = %s
                WHERE run_id = %s
            """, (total_extracted, total_loaded, total_errors, etl_run_id))
            db_conn.commit()
            logging.info(f"Run log updated: run_id={etl_run_id}")
        except Exception as e:
            logging.error(f"Failed to update run log: {e}")

    cursor.close()
    db_conn.close()

    # Print summary
    logging.info("=" * 80)
    logging.info("ETL Process Complete")
    logging.info(f"Total Extracted: {total_extracted}")
    logging.info(f"Total Loaded: {total_loaded}")
    logging.info(f"Total Errors: {total_errors}")
    logging.info("=" * 80)
