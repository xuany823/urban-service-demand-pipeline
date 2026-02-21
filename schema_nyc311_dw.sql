-- 1) Create database (schema)
CREATE DATABASE IF NOT EXISTS nyc311_dw
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;

USE nyc311_dw;

-- 2) Dimension tables (lookup tables)

CREATE TABLE IF NOT EXISTS dim_status (
  status_id INT AUTO_INCREMENT PRIMARY KEY,
  status_name VARCHAR(64) NOT NULL,
  UNIQUE KEY uq_status_name (status_name)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS dim_channel (
  channel_id INT AUTO_INCREMENT PRIMARY KEY,
  channel_type VARCHAR(64) NOT NULL,
  UNIQUE KEY uq_channel_type (channel_type)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS dim_agency (
  agency_id INT AUTO_INCREMENT PRIMARY KEY,
  agency_code VARCHAR(32) NOT NULL,
  agency_name VARCHAR(255),
  UNIQUE KEY uq_agency (agency_code, agency_name)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS dim_problem (
  problem_id INT AUTO_INCREMENT PRIMARY KEY,
  problem_type VARCHAR(255) NOT NULL,
  problem_detail VARCHAR(255),
  UNIQUE KEY uq_problem (problem_type, problem_detail)
) ENGINE=InnoDB;

-- 3) Standalone Location component tables

-- 3a) Address
CREATE TABLE IF NOT EXISTS dim_address (
  address_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  incident_address VARCHAR(255),
  street_name VARCHAR(255),
  cross_street_1 VARCHAR(255),
  cross_street_2 VARCHAR(255),
  intersection_street_1 VARCHAR(255),
  intersection_street_2 VARCHAR(255),
  city VARCHAR(255),
  incident_zip VARCHAR(20),
  borough VARCHAR(64),
  bbl VARCHAR(32),
  address_type VARCHAR(64),
  location_type VARCHAR(255),
  facility_type VARCHAR(255)
) ENGINE=InnoDB;

CREATE INDEX idx_address_borough_zip ON dim_address(borough, incident_zip);

-- 3b) Neighborhood
CREATE TABLE IF NOT EXISTS dim_neighborhood (
  neighborhood_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  landmark VARCHAR(255),
  community_board VARCHAR(64),
  council_district VARCHAR(64),
  police_precinct VARCHAR(64)
) ENGINE=InnoDB;

-- 3c) Park Information
CREATE TABLE IF NOT EXISTS dim_park (
  park_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  park_facility_name VARCHAR(255),
  park_borough VARCHAR(64)
) ENGINE=InnoDB;

-- 3d) Highway Information
CREATE TABLE IF NOT EXISTS dim_highway (
  highway_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  bridge_highway_name VARCHAR(255),
  bridge_highway_direction VARCHAR(64),
  road_ramp VARCHAR(255),
  bridge_highway_segment VARCHAR(255)
) ENGINE=InnoDB;

-- 3e) Taxi Information
CREATE TABLE IF NOT EXISTS dim_taxi (
  taxi_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  vehicle_type VARCHAR(64),
  taxi_company_borough VARCHAR(64),
  taxi_pick_up_location VARCHAR(255)
) ENGINE=InnoDB;

-- 3f) Geography
CREATE TABLE IF NOT EXISTS dim_geography (
  geography_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  x_coordinate_state_plane DECIMAL(12,2),
  y_coordinate_state_plane DECIMAL(12,2),
  latitude DECIMAL(10,6),
  longitude DECIMAL(10,6),
  location_text VARCHAR(255)   -- raw "Location" text field
) ENGINE=InnoDB;

-- 4) Location hub table (ties the location components together)
-- This makes it easy for the fact table to reference "one location_id"
CREATE TABLE IF NOT EXISTS dim_location (
  location_id BIGINT AUTO_INCREMENT PRIMARY KEY,

  address_id BIGINT NULL,
  neighborhood_id BIGINT NULL,
  park_id BIGINT NULL,
  highway_id BIGINT NULL,
  taxi_id BIGINT NULL,
  geography_id BIGINT NULL,

  CONSTRAINT fk_loc_address
    FOREIGN KEY (address_id) REFERENCES dim_address(address_id),

  CONSTRAINT fk_loc_neighborhood
    FOREIGN KEY (neighborhood_id) REFERENCES dim_neighborhood(neighborhood_id),

  CONSTRAINT fk_loc_park
    FOREIGN KEY (park_id) REFERENCES dim_park(park_id),

  CONSTRAINT fk_loc_highway
    FOREIGN KEY (highway_id) REFERENCES dim_highway(highway_id),

  CONSTRAINT fk_loc_taxi
    FOREIGN KEY (taxi_id) REFERENCES dim_taxi(taxi_id),

  CONSTRAINT fk_loc_geography
    FOREIGN KEY (geography_id) REFERENCES dim_geography(geography_id)
) ENGINE=InnoDB;

CREATE INDEX idx_loc_address ON dim_location(address_id);
CREATE INDEX idx_loc_geo ON dim_location(geography_id);

-- 5) Fact table (main request record)
CREATE TABLE IF NOT EXISTS fact_service_request (
  -- Incident/Problem Status
  unique_key BIGINT PRIMARY KEY,

  -- Incident/Problem time
  created_ts DATETIME NULL,
  closed_ts DATETIME NULL,
  resolution_action_updated_ts DATETIME NULL,
  due_ts DATETIME NULL,

  -- Incident/Problem contents
  additional_details TEXT,
  resolution_description TEXT,

  -- Foreign keys to dimensions
  status_id INT NULL,
  channel_id INT NULL,
  agency_id INT NULL,
  problem_id INT NULL,
  location_id BIGINT NULL,

  -- Optional ETL metadata
  etl_loaded_ts TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_fact_status
    FOREIGN KEY (status_id) REFERENCES dim_status(status_id),

  CONSTRAINT fk_fact_channel
    FOREIGN KEY (channel_id) REFERENCES dim_channel(channel_id),

  CONSTRAINT fk_fact_agency
    FOREIGN KEY (agency_id) REFERENCES dim_agency(agency_id),

  CONSTRAINT fk_fact_problem
    FOREIGN KEY (problem_id) REFERENCES dim_problem(problem_id),

  CONSTRAINT fk_fact_location
    FOREIGN KEY (location_id) REFERENCES dim_location(location_id)
) ENGINE=InnoDB;

-- Helpful indexes for reporting
CREATE INDEX idx_fact_created_ts ON fact_service_request(created_ts);
CREATE INDEX idx_fact_status ON fact_service_request(status_id);
CREATE INDEX idx_fact_agency ON fact_service_request(agency_id);
CREATE INDEX idx_fact_problem ON fact_service_request(problem_id);
CREATE INDEX idx_fact_location ON fact_service_request(location_id);

-- 6) ETL Checkpoint table to track last processed record
CREATE TABLE IF NOT EXISTS etl_checkpoint (
  checkpoint_id INT AUTO_INCREMENT PRIMARY KEY,
  last_extracted_timestamp DATETIME NULL,
  last_run_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  records_loaded INT NOT NULL DEFAULT 0,
  etl_status VARCHAR(50) DEFAULT 'completed',
  error_message TEXT NULL
) ENGINE=InnoDB;

-- 7) ETL Log table to track ETL runs and errors in more detail
CREATE TABLE etl_run_log (
  run_id INT AUTO_INCREMENT PRIMARY KEY,
  start_time TIMESTAMP,
  end_time TIMESTAMP,
  status VARCHAR(50),
  records_extracted INT,
  records_loaded INT,
  errors_count INT,
  error_summary TEXT
); ENGINE=InnoDB;


-- ============================================================
-- Schema Cleanup + Standard Audit Columns
-- 1. Remove legacy etl_loaded_ts from fact table
-- 2. Add standardized audit columns to all tables
-- ============================================================

USE nyc311_dw;

-- ------------------------------------------------------------
-- 1) Remove legacy ETL column from fact table
-- ------------------------------------------------------------
ALTER TABLE fact_service_request
  DROP COLUMN etl_loaded_ts;

-- ------------------------------------------------------------
-- 2) Add standardized audit columns to ALL tables
-- ------------------------------------------------------------

ALTER TABLE dim_status
  ADD COLUMN etl_load_created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP;

ALTER TABLE dim_channel
  ADD COLUMN etl_load_created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP;

ALTER TABLE dim_agency
  ADD COLUMN etl_load_created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP;

ALTER TABLE dim_problem
  ADD COLUMN etl_load_created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP;

ALTER TABLE dim_address
  ADD COLUMN etl_load_created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP;

ALTER TABLE dim_neighborhood
  ADD COLUMN etl_load_created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP;

ALTER TABLE dim_park
  ADD COLUMN etl_load_created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP;

ALTER TABLE dim_highway
  ADD COLUMN etl_load_created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP;

ALTER TABLE dim_taxi
  ADD COLUMN etl_load_created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP;

ALTER TABLE dim_geography
  ADD COLUMN etl_load_created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP;

ALTER TABLE dim_location
  ADD COLUMN etl_load_created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP;

ALTER TABLE fact_service_request
  ADD COLUMN etl_load_created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP;
