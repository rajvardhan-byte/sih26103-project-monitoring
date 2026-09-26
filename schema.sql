-- PostgreSQL Database Schema for Project Monitoring Platform (SIH26103)

DROP TABLE IF EXISTS project_milestones CASCADE;
DROP TABLE IF EXISTS projects CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Registered Users Table (Role-Based Access Control & Registration)
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50) CHECK (role IN ('Government Officer', 'Contractor', 'Site Engineer')) NOT NULL,
    organization VARCHAR(100) NOT NULL,
    registered_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Infrastructure Projects Table
CREATE TABLE projects (
    project_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    cost VARCHAR(50) NOT NULL,
    progress INT CHECK (progress BETWEEN 0 AND 100) DEFAULT 0,
    risk_level VARCHAR(20) CHECK (risk_level IN ('Low', 'Medium', 'High')) DEFAULT 'Low',
    predicted_delay VARCHAR(50) DEFAULT '0 Months',
    predicted_overrun VARCHAR(50) DEFAULT '₹0 Cr',
    contractor VARCHAR(150) NOT NULL,
    last_reported DATE DEFAULT CURRENT_DATE
);

-- Initial Seed Data
INSERT INTO users (full_name, email, password, role, organization) VALUES 
('Rajesh Kumar', 'rajesh.k@mospi.gov.in', 'password123', 'Government Officer', 'MoSPI Maharashtra');

INSERT INTO projects (name, cost, progress, risk_level, predicted_delay, predicted_overrun, contractor) VALUES 
('Nagpur Outer Ring Road (Sec 3)', '₹1,250 Cr', 62, 'High', '8 Months', '₹45 Cr', 'L&T Infrastructure Ltd.'),
('Pune-Nashik High-Speed Rail Link', '₹16,000 Cr', 40, 'Medium', '3 Months', '₹120 Cr', 'Mega Infra Corp'),
('Mumbai Metro Line 4 Extension', '₹14,500 Cr', 85, 'Low', '0 Months', '₹0 Cr', 'Tata Projects');