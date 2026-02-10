# Monitoring Urban Service Demand Through a Production-Ready NYC 311 Data Pipeline #

## Project Overview
This project builds a production-style data pipeline using the NYC 311 Service Requests dataset. The pipeline ingests continuously updated public service request data, loads it into a MySQL database, applies SQL-based transformations, and produces analytics-ready outputs. The goal is to demonstrate how real-world urban service data can be processed and monitored through a reproducible, version-controlled data engineering workflow.

---
- **Team Members:**
  - Xuan Wang  
  - Michael Ha  
  - Lei Lin  

GitHub Repository:  
https://github.com/xuany823/ADS507-FinalProject-Team1  

---

## Business Objectives
- Create a ETL pipeline for data team to extract data for further reporting and analysis.

## Project Objectives
- Design and implement a reproducible ETL pipeline using real-world, continuously updating data  
- Ingest NYC 311 service request data through API or CSV into MySQL  
- Perform SQL transformations to clean, normalize, and aggregate raw data   
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

**Sample Key Fields Include:**
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
Data Transformations
↓
MySQL

---

## Team Contributions
All team members contribute equally and collaborate on:
- Dataset research and validation  
- Project design and planning  
- ETL pipeline development  
- Database schema design  
- Data transformations  
- Documentation & Presentation

---
## Method Used
This project uses data engineering, database management, and API integration:
- ETL (Extract, Transform, Load)
- MySQL Queries and Functions
- API Integration

---
## Technology Used
- Programming and Scripting: Python, Jupyter Notebooks
- Database Management: MySQL
- Cloud Infrastructure: under deciding--- Microsoft Azure (database hosting)
- Version Control & Collaboration: Git, GitHub
- Development Tools: VS Code, MySQL Workbench
- APIs: NYC 311 Service Requests APIs  



---
This project documentation was revised with guidance from OpenAI’s ChatGPT (2026).
- Roadblocks: None at this stage  


