**Monitoring Urban Service Demand Through a Production-Ready NYC 311 Data Pipeline**

This project builds a production-style data pipeline using the NYC 311 Service Requests dataset. The pipeline ingests continuously updated public service request data, loads it into a MySQL database, applies SQL-based transformations, and produces analytics-ready outputs and visualizations. The goal is to demonstrate how real-world urban service data can be processed and monitored through a reproducible, version-controlled data engineering workflow.

---
- **Team Members:**
  - Xuan Wang  
  - Michael Ha  
  - Lei Lin  

GitHub Repository:  
https://github.com/xuany823/ADS507-FinalProject-Team1  

---

## Project Objectives
- Design and implement a fully reproducible ETL pipeline using real-world, continuously updating data  
- Ingest NYC 311 service request data through API or CSV into MySQL  
- Perform SQL transformations to clean, normalize, and aggregate raw data  
- Create analytics-ready tables for trend analysis and reporting  
- Demonstrate production concepts such as pipeline triggering, persistence, and version control  

---

## Dataset
**Name:** NYC 311 Service Requests Dataset  
**Source:** NYC Open Data  
**URL:**  
https://data.cityofnewyork.us/Social-Services/311-Service-Requests/erm2-nwe9  

**Description:**
- Contains records of non-emergency service requests submitted by NYC residents  
- Updated continuously with new requests added daily  
- Accessible via:
  - CSV bulk downloads  
  - Socrata REST API for incremental ingestion  

**Key Fields Include:**
- Created and closed timestamps  
- Complaint type and descriptor  
- Responsible agency  
- Request status (open/closed)  
- Borough, ZIP code, latitude, and longitude  

The dataset is large enough to simulate real-world production pipelines while allowing filtering for recent time periods to keep processing manageable.

---

## Planned Pipeline Architecture
NYC Open Data API / CSV
↓
Python ETL
↓
MySQL
↓
SQL Transformations
↓
Analytics Tables & Visualizations

---

## Team Contributions
All team members contribute equally and collaborate on:
- Dataset research and validation  
- Project design and planning  
- ETL pipeline development  
- Database schema design  
- SQL transformations  
- Documentation and visualization  

---

## Status
- Team meetings in last two weeks: 2  
- Roadblocks: None at this stage  

---
