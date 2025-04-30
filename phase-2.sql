PRAGMA foreign_keys=OFF;

-- Drop all tables
DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS application;
DROP TABLE IF EXISTS academicInformation;
DROP TABLE IF EXISTS priorDegree;
DROP TABLE IF EXISTS recommendationLetter;
DROP TABLE IF EXISTS reviewForm;
DROP TABLE IF EXISTS Student;
DROP TABLE IF EXISTS faculty;
DROP TABLE IF EXISTS grad_secretary;
DROP TABLE IF EXISTS admin;
DROP TABLE IF EXISTS alumni;
DROP TABLE IF EXISTS course;
DROP TABLE IF EXISTS transcript;
DROP TABLE IF EXISTS schedule;
DROP TABLE IF EXISTS course_prerequisite;
DROP TABLE IF EXISTS applied_for_grad;
DROP TABLE IF EXISTS form1;
DROP TABLE IF EXISTS form1_course;

-- Now enable foreign keys for table creation and data insertion
PRAGMA foreign_keys=ON;

-- Create tables and insert data as before
-- User table with roles now
CREATE TABLE user (
    UID                     INTEGER not null PRIMARY KEY,
    role                    varchar(50) not null CHECK (role IN ('Applicant', 'Student', 'Faculty', 'GS', 'CAC', 'Admin', 'Alumni')),
    password                varchar(50) not null,
    firstName               varchar(50) not null,
    lastName                varchar(50) not null,
    ssn                     varchar(50) not null,
    email                   varchar(50) not null UNIQUE,
    phone                   varchar(50) not null,
    address                 varchar(50) not null,
    address2                varchar(50)
);

CREATE TABLE student (
  UID             INTEGER not null PRIMARY KEY,
  advisor_id      INTEGER,
  GPA             DECIMAL,
  program   VARCHAR(50) CHECK (program IN ('Masters', 'PhD')),
  thesis_status   VARCHAR(50),
  advising_hold   BOOLEAN DEFAULT TRUE,
  FOREIGN KEY (UID) REFERENCES user(UID),
  FOREIGN KEY (advisor_id) REFERENCES faculty(UID)
);

CREATE TABLE faculty (
  UID             INTEGER not null PRIMARY KEY,
  dept            VARCHAR(50) not null,
  FOREIGN KEY (UID) REFERENCES user(UID)
);

CREATE TABLE grad_secretary (
  UID           INTEGER not null PRIMARY KEY,
  office        VARCHAR(50),
  foreign key (UID) references user(UID)
);

CREATE TABLE admin (
  UID           INTEGER not null PRIMARY KEY,
  access_level  VARCHAR(50),
  foreign key (UID) references user(UID)
);

CREATE TABLE alumni (
  UID          INTEGER not null PRIMARY KEY,
  grad_year    INTEGER,
  degree       VARCHAR(50),
  foreign key (UID) references user(UID)
);

CREATE TABLE course (
    course_id INT PRIMARY KEY,
    dept VARCHAR(10),
    course_num VARCHAR(10),
    title VARCHAR(100),
    credits INT,
    instructor_id INT,
    FOREIGN KEY (instructor_id) REFERENCES faculty(UID)
);

CREATE TABLE course_prerequisite (
    course_id INT,
    prereq_id INT,
    PRIMARY KEY (course_id, prereq_id),
    FOREIGN KEY (course_id) REFERENCES Course(course_id),
    FOREIGN KEY (prereq_id) REFERENCES Course(course_id)
);

CREATE TABLE schedule (
    course_id INT,  
    semester VARCHAR(20),
    section INT,
    year INT,
    day VARCHAR(1) CHECK (day IN ('M','T','W','R','F')),
    time_slot VARCHAR(20) CHECK (time_slot IN ('15:00-17:30', '16:00-18:30', '18:00-20:30')),
    instructor_id INT,
    PRIMARY KEY (course_id, section, semester, year),
    FOREIGN KEY (course_id) REFERENCES course(course_id),
    FOREIGN KEY (instructor_id) REFERENCES faculty(UID)
);

CREATE TABLE transcript (
    Student_uid INT,
    course_id INT,
    section INT,
    semester VARCHAR(20),
    year INT,
    grade VARCHAR(2) CHECK (grade IN ('A','A-','B+','B','B-','C+','C','F','IP')),
    graded BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (Student_uid, course_id, section, semester),
    FOREIGN KEY (Student_uid) REFERENCES User(UID),
    FOREIGN KEY (course_id, section, semester, year) REFERENCES schedule(course_id, section, semester, year) ON DELETE CASCADE ON UPDATE CASCADE
);

-- Application status tracking with application date
CREATE TABLE application (
    UID                     INTEGER not null PRIMARY KEY,
    applicationStatus       varchar(50) not null CHECK (applicationStatus IN ('Incomplete', 'Complete and Under Review','Reviewed', 'Admitted', 'Rejected')),
    applySemester           varchar(10) not null CHECK (applySemester IN ('Fall', 'Spring')),
    applyYear               varchar(4) not null,
    decisionType            varchar(20) CHECK (decisionType IN ('Admit with Aid', 'Admit without Aid', 'Reject', NULL)),
    recommendedAdvisor      varchar(100),
    deficiencyCourses       TEXT,
    rejectReason            varchar(1) CHECK (rejectReason IN ('A', 'B', 'C', 'D', 'E', NULL)),
    finalDecisionDate       DATE,
    FOREIGN KEY (UID) REFERENCES user(UID)
);

-- Academic information normalized with TOEFL scores
CREATE TABLE academicInformation (
  UID                       INTEGER not null PRIMARY KEY,
  degree                    varchar(50) not null CHECK (degree IN ('MS', 'PhD')),
  GRE_Verbal                varchar(50),
  GRE_Quant                 varchar(50),
  GRE_Year                  varchar(4),
  GRE_Advanced              varchar(50),
  GRE_Subject               varchar(50),
  TOEFL_Score               varchar(50),
  TOEFL_Date                DATE,
  areasOfInterest           varchar(100),
  priorWorkExp              varchar(200),
  transcripts               varchar(50),
  applySemester           varchar(10) CHECK (applySemester IN ('Fall', 'Spring')),
  applyYear               varchar(4),
  FOREIGN KEY (UID) REFERENCES user(UID)
);

-- Prior degrees in separate table (one-to-many)
CREATE TABLE priorDegree (
  id                        INTEGER PRIMARY KEY AUTOINCREMENT,
  UID                       INTEGER not null,
  degreeName                varchar(50) not null,
  institution               varchar(100) not null,
  major                     varchar(50) not null,
  GPA                       DECIMAL(3,2),
  year                      varchar(4),
  FOREIGN KEY (UID) REFERENCES user(UID)
);

-- Recommendation letters
CREATE TABLE recommendationLetter (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    UID                     INTEGER not null,
    writerName              varchar(50) not null,
    writerEmail             varchar(50) not null,
    writerAffiliation       varchar(100),
    letter                  TEXT,
    submissionDate          DATE,
    token                   VARCHAR(36) UNIQUE,
    status                  VARCHAR(10) DEFAULT 'Pending' CHECK (status IN ('Pending', 'Submitted')),
    -- For review form
    rating                  INTEGER CHECK (rating BETWEEN 1 AND 5),
    isGeneric               BOOLEAN,
    isCredible              BOOLEAN,
    FOREIGN KEY (UID) REFERENCES user(UID)
);

-- faculty review form with GAS rating system
CREATE TABLE reviewForm (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    UID                     varchar(8) not null,
    reviewerUID             varchar(8) not null,
    reviewDate              DATE not null,
    GAS_Rating              INTEGER CHECK (GAS_Rating BETWEEN 0 AND 3),
    comments                TEXT,
    FOREIGN KEY (UID) REFERENCES user(UID),
    FOREIGN KEY (reviewerUID) REFERENCES user(UID)
);

CREATE TABLE applied_for_grad (
  application_id   INTEGER not null PRIMARY KEY,
  UID              INTEGER not null,
  cleared          VARCHAR(50) not null CHECK (cleared IN ('Cleared', 'Not Cleared')),
  semester         VARCHAR(50) not null CHECK (semester IN ('Fall', 'Spring')),
  year             INTEGER not null,
  foreign key (UID) references Student(UID)
);

CREATE TABLE form1 (
  form1_id         INTEGER not null PRIMARY KEY,
  UID              INTEGER not null,
  status           VARCHAR(50) not null CHECK (status IN ('Submitted', 'Approved', 'Rejected')),
  foreign key (UID) references Student(UID)
);

CREATE TABLE form1_course (
  form1_id         INTEGER not null,
  course_id        INTEGER not null,
  primary key (form1_id, course_id),
  foreign key (form1_id) references form1(form1_id),
  foreign key (course_id) references course(course_id)
);


INSERT INTO user (UID, firstName, lastName, email, password, role, ssn, phone, address, address2) VALUES
(10000001, 'adminuser', 'Admin', 'adminuser@example.com', 'adminpass123', 'Admin', '000-00-0001', '555-0001', 'Admin Blvd', NULL),
(20000001, 'Taylor', 'Swift', 'taylor.swift@uni.edu', 'pass', 'Student', '000-00-0002', '555-0002', '123 Music Ave', NULL),
(20000002, 'Harry', 'Styles', 'harry.styles@uni.edu', 'pass', 'Student', '000-00-0003', '555-0003', '234 Style St', NULL),
(20000003, 'Zendaya', 'Coleman', 'zendaya@uni.edu', 'pass', 'Student', '000-00-0004', '555-0004', '345 Fame Blvd', NULL),
(20000004, 'Timothee', 'Chalamet', 'timothee@uni.edu', 'pass', 'Student', '000-00-0005', '555-0005', '456 Actor Rd', NULL),
(20000005, 'Emma', 'Watson', 'emma.watson@uni.edu', 'pass', 'Student', '000-00-0006', '555-0006', '567 Magic Ln', NULL),
(20000006, 'Drake', 'Graham', 'drake@uni.edu', 'pass', 'Student', '000-00-0007', '555-0007', '678 Rap St', NULL),
(20000007, 'Ariana', 'Grande', 'ariana@uni.edu', 'pass', 'Student', '000-00-0008', '555-0008', '789 Pop Ct', NULL),
(20000008, 'Billie', 'Eilish', 'billieE@uni.edu', 'pass', 'Student', '000-00-0009', '555-0009', '890 Alt Rd', NULL),
(20000009, 'Dwayne', 'Johnson', 'dwayne@uni.edu', 'pass', 'Student', '000-00-0010', '555-0010', '901 Rock Blvd', NULL),
(20000010, 'Selena', 'Gomez', 'selena@uni.edu', 'pass', 'Student', '000-00-0011', '555-0011', '012 Star Way', NULL),
(88888888, 'Billie', 'Holiday', 'billie@uni.edu', 'billiepass', 'Student', '000-00-0012', '555-0012', '100 Jazz St', NULL),
(99999991, 'Diana', 'Krall', 'diana@uni.edu', 'dianapass', 'Student', '000-00-0013', '555-0013', '101 Blues St', NULL),
(30000001, 'Leonardo', 'DiCaprio', 'leo@alumni.edu', 'pass', 'Alumni', '000-00-0014', '555-0014', 'alumni Way', NULL),
(30000002, 'Natalie', 'Portman', 'natalie@alumni.edu', 'pass', 'Alumni', '000-00-0015', '555-0015', 'alumni Way', NULL),
(30000003, 'Morgan', 'Freeman', 'morgan@alumni.edu', 'pass', 'Alumni', '000-00-0016', '555-0016', 'alumni Way', NULL),
(40000001, 'Oprah', 'Winfrey', 'oprah.gs@uni.edu', 'pass', 'GS', '000-00-0017', '555-0017', 'Grad Sec St', NULL),
(40000002, 'Ellen', 'DeGeneres', 'ellen.gs@uni.edu', 'pass', 'GS', '000-00-0018', '555-0018', 'Grad Sec St', NULL),
(40000003, 'Jimmy', 'Fallon', 'jimmy.gs@uni.edu', 'pass', 'GS', '000-00-0019', '555-0019', 'Grad Sec St', NULL),
(11111111, 'Grace', 'gs', 'gs@uni.edu', 'gspass', 'GS', '000-00-0020', '555-0020', 'gs Office', NULL),
(50000001, 'Albert', 'Einstein', 'einstein@uni.edu', 'pass', 'Faculty', '000-00-0021', '555-0021', 'Science Hall', NULL),
(50000002, 'Marie', 'Curie', 'curie@uni.edu', 'pass', 'Faculty', '000-00-0022', '555-0022', 'Science Hall', NULL),
(50000003, 'Isaac', 'Newton', 'newton@uni.edu', 'pass', 'Faculty', '000-00-0023', '555-0023', 'Science Hall', NULL),
(50000004, 'Katherine', 'Johnson', 'kjohnson@uni.edu', 'pass', 'Faculty', '000-00-0024', '555-0024', 'Science Hall', NULL),
(50000005, 'Ada', 'Lovelace', 'ada@uni.edu', 'pass', 'Faculty', '000-00-0025', '555-0025', 'Science Hall', NULL),
(22222222, 'Narahari', 'Prof', 'narahari@uni.edu', 'naraharipass', 'Faculty', '000-00-0026', '555-0026', 'Science Hall', NULL),
(33333333, 'Choi', 'Prof', 'choi@uni.edu', 'choipass', 'Faculty', '000-00-0027', '555-0027', 'Science Hall', NULL),
(60000001, 'CAC', 'CAC', 'cac@uni.edu', 'pass', 'CAC', '020-00-0027', '525-0027', 'Science Hall', NULL);


-- INSTRUCTORS
INSERT INTO faculty (UID, dept) VALUES
(50000001, 'CSCI'), 
(50000002, 'CSCI'), 
(50000003, 'CSCI'), 
(50000004, 'CSCI'), 
(50000005, 'CSCI'),
(22222222, 'CSCI'), 
(33333333, 'CSCI'),
(60000001, 'CSCI');

-- populate with additional info - about each typeuser, grad year, address, etc
INSERT INTO Student (UID, advisor_id, GPA, program, thesis_status, advising_hold) VALUES
(20000001, 50000001, 3.92, 'Masters', 'Incomplete', FALSE),
(20000002, 50000001, 3.88, 'PhD', 'Complete', FALSE),
(20000003, 50000002, 3.76, 'Masters', 'Incomplete', FALSE),
(20000004, 50000002, 3.91, 'PhD', 'Incomplete', FALSE),
(20000005, 50000001, 3.85, 'Masters', 'Complete', FALSE),
(20000006, 50000001, 3.67, 'Masters', 'Complete', FALSE),
(20000007, 50000002, 3.89, 'PhD', 'Incomplete', FALSE),
(20000008, 50000001, 3.95, 'Masters', 'Complete', FALSE),
(20000009, 50000001, 3.79, 'PhD', 'Incomplete', FALSE),
(20000010, 50000002, 3.87, 'Masters', 'Complete', FALSE),
(88888888, 50000002, 3.93, 'Masters', 'Complete', FALSE);

INSERT INTO alumni (UID, grad_year, degree) VALUES
(30000001, 2020, 'Masters'),
(30000002, 2019, 'PhD'),
(30000003, 2018, 'Masters');

-- GRAD SECRETARIES
INSERT INTO grad_secretary (UID, office) VALUES
(40000001, 'Room 101'), 
(40000002, 'Room 102'), 
(40000003, 'Room 103'),
(11111111, 'gs Office');

INSERT INTO course (course_id, dept, course_num, title, credits, instructor_id) VALUES
(1, 'CSCI', '6221', 'SW Paradigms', 3, 50000001),
(100, 'CSCI', '6461', 'Computer Architecture', 3, 22222222),
(101, 'CSCI', '6212', 'Algorithms', 3, 33333333),
(4, 'CSCI', '6220', 'Machine Learning', 3, 50000001),
(5, 'CSCI', '6232', 'Networks 1', 3, 50000002),
(6, 'CSCI', '6233', 'Networks 2', 3, 50000003),
(7, 'CSCI', '6241', 'Database 1', 3, 50000004),
(8, 'CSCI', '6242', 'Database 2', 3, 50000004),
(9, 'CSCI', '6246', 'Compilers', 3, 50000005),
(10, 'CSCI', '6260', 'Multimedia', 3, 50000005),
(11, 'CSCI', '6251', 'Cloud Computing', 3, 22222222),
(12, 'CSCI', '6254', 'SW Engineering', 3, 50000002),
(13, 'CSCI', '6262', 'Graphics 1', 3, 50000003),
(14, 'CSCI', '6283', 'Security 1', 3, 50000004),
(15, 'CSCI', '6284', 'Cryptography', 3, 50000005),
(16, 'CSCI', '6286', 'Network Security', 3, 50000001),
(17, 'CSCI', '6325', 'Algorithms 2', 3, 50000002),
(18, 'CSCI', '6339', 'Embedded Systems', 3, 50000003),
(19, 'CSCI', '6384', 'Cryptography 2', 3, 33333333),
(20, 'ECE', '6241', 'Communication Theory', 3, 50000005),
(21, 'ECE', '6242', 'Information Theory', 2, 50000001),
(22, 'MATH', '6210', 'Logic', 2, 50000002);

INSERT INTO schedule (course_id, semester, section, year, day, time_slot, instructor_id) VALUES
(1, 'Fall', 1, 2021, 'M', '15:00-17:30', 50000001),       -- CSCI 6221 Fall 2021
(100, 'Spring', 1, 2020, 'T', '16:00-18:30', 22222222),   -- CSCI 6461 Spring 2020
(101, 'Fall', 1, 2022, 'W', '15:00-17:30', 33333333),     -- CSCI 6212 Fall 2022
(4, 'Spring', 1, 2020, 'R', '18:00-20:30', 50000001),     -- CSCI 6220 Spring 2020
(5, 'Fall', 1, 2023, 'F', '15:00-17:30', 50000002),       -- CSCI 6232 Fall 2023
(6, 'Spring', 1, 2022, 'M', '16:00-18:30', 50000003),
(1, 'Fall', 1, 2024, 'M', '15:00-17:30', 50000001),
(100, 'Fall', 1, 2024, 'M', '15:00-17:30', 22222222),
(101, 'Fall', 1, 2024, 'W', '15:00-17:30', 33333333),
(4, 'Fall', 1, 2024, 'R', '15:00-17:30', 50000001),
(5, 'Fall', 1, 2024, 'F', '16:00-18:30', 50000002),
(6, 'Fall', 1, 2024, 'M', '18:00-20:30', 50000003),
(7, 'Fall', 1, 2024, 'T', '15:00-17:30', 50000004),
(8, 'Fall', 1, 2024, 'W', '15:00-17:30', 50000004),
(9, 'Fall', 1, 2024, 'R', '16:00-18:30', 50000005),
(10, 'Fall', 1, 2024, 'F', '18:00-20:30', 50000005),
(11, 'Fall', 1, 2024, 'M', '15:00-17:30', 22222222),
(12, 'Fall', 1, 2024, 'T', '16:00-18:30', 50000002),
(13, 'Fall', 1, 2024, 'W', '18:00-20:30', 50000003),
(14, 'Fall', 1, 2024, 'R', '15:00-17:30', 50000004),
(15, 'Fall', 1, 2024, 'F', '16:00-18:30', 50000005),
(16, 'Fall', 1, 2024, 'M', '18:00-20:30', 50000001),
(17, 'Fall', 1, 2024, 'T', '15:00-17:30', 50000002),
(18, 'Fall', 1, 2024, 'W', '15:00-17:30', 50000003),
(19, 'Fall', 1, 2024, 'R', '16:00-18:30', 33333333),
(20, 'Fall', 1, 2024, 'F', '18:00-20:30', 50000005),
(21, 'Fall', 1, 2024, 'M', '15:00-17:30', 50000001),
(22, 'Fall', 1, 2024, 'T', '16:00-18:30', 50000002);

-- Insert prerequisites
INSERT INTO course_prerequisite (course_id, prereq_id) VALUES
-- Networks 2 prerequisites
(6, 5), -- CSCI 6233 requires CSCI 6232

-- Database 2 prerequisites
(8, 7), -- CSCI 6242 requires CSCI 6241

-- Compilers prerequisites
(9, 100), -- CSCI 6246 requires CSCI 6461
(9, 101), -- CSCI 6246 requires CSCI 6212

-- Cloud Computing prerequisites
(11, 100), -- CSCI 6251 requires CSCI 6461

-- SW Engineering prerequisites
(12, 1), -- CSCI 6254 requires CSCI 6221

-- Security 1 prerequisites
(14, 101), -- CSCI 6283 requires CSCI 6212

-- Cryptography prerequisites
(15, 101), -- CSCI 6284 requires CSCI 6212

-- Network Security prerequisites
(16, 14), -- CSCI 6286 requires CSCI 6283
(16, 5),  -- CSCI 6286 requires CSCI 6232

-- Algorithms 2 prerequisites
(17, 101), -- CSCI 6325 requires CSCI 6212

-- Embedded Systems prerequisites
(18, 100), -- CSCI 6339 requires CSCI 6461
(18, 101), -- CSCI 6339 requires CSCI 6212

-- Cryptography 2 prerequisites
(19, 15); -- CSCI 6384 requires CSCI 6284

INSERT INTO transcript (Student_uid, course_id, section, semester, year, grade, graded) VALUES
-- Students
(20000001, 1, 1, 'Fall', 2024, 'IP', FALSE),
(20000002, 100, 1, 'Fall', 2024, 'IP', FALSE),
(20000003, 101, 1, 'Fall', 2024, 'IP', FALSE),
(20000004, 4, 1, 'Fall', 2024, 'IP', FALSE),
(20000005, 5, 1, 'Fall', 2024, 'IP', FALSE),
(20000006, 6, 1, 'Fall', 2024, 'IP', FALSE),
(20000007, 7, 1, 'Fall', 2024, 'IP', FALSE),
(20000008, 8, 1, 'Fall', 2024, 'IP', FALSE),
(20000009, 9, 1, 'Fall', 2024, 'IP', FALSE),
(20000010, 10, 1, 'Fall', 2024, 'IP', FALSE),
(88888888, 100, 1, 'Fall', 2024, 'IP', FALSE),
(88888888, 101, 1, 'Fall', 2024, 'IP', FALSE),
-- alumni
(30000001, 1, 1, 'Fall', 2021, 'A', TRUE),
(30000001, 100, 1, 'Spring', 2020, 'A-', TRUE),
(30000002, 101, 1, 'Fall', 2022, 'B+', TRUE),
(30000002, 4, 1, 'Spring', 2020, 'A', TRUE),
(30000003, 5, 1, 'Fall', 2023, 'A-', TRUE),
(30000003, 6, 1, 'Spring', 2022, 'B', TRUE);

-- ads
INSERT INTO user VALUES(55555555, 'Student', 'password', 'Paul', 'McCartney', 1111, 'paulmccartney@email.com', 12345678, 'Address', NULL);
INSERT INTO user VALUES(66666666, 'Student', 'password', 'George', 'Harrison', 2222, 'georgeharrison@email.com', 87654321, 'Address', NULL);
INSERT INTO user VALUES(99999999, 'Student', 'password', 'Ringo', 'Starr', 3333, 'ringostarr@email.com', 1111111111, 'Address', NULL);
INSERT INTO user VALUES(12345678, 'Alumni', 'password', 'Eric', 'Clapton', 4444, 'ericclapton@email.com', 222222222, 'Address', NULL);
INSERT INTO user VALUES(12121212, 'GS', 'password', 'John', 'Snow', 5555, 'johnsnow@email.com', 3333333333, 'Address', NULL);
INSERT INTO user VALUES(22222221, 'Faculty', 'password', 'Bhagirath', 'Narahari', 6666, 'bnarahari@email.com', 4444444444, 'Address', NULL);
INSERT INTO user VALUES(33333331, 'Faculty', 'password', 'Gabe', 'Parmer', 7777, 'gparmer@email.com', 5555555555, 'Address', NULL);
INSERT INTO user VALUES(13131313, 'Admin', 'password', 'Jett', 'Jacobs', 8888, 'jettjacobs@email.com', 6666666666, 'Address', NULL);

INSERT INTO faculty VALUES(22222221, 'CSCI');
INSERT INTO faculty VALUES(33333331, 'CSCI');
INSERT INTO student VALUES(55555555, 22222221, 0.0, 'Masters', 'Incomplete', FALSE);
INSERT INTO student VALUES(66666666, 22222221, 0.0, 'Masters', 'Incomplete', FALSE);
INSERT INTO student VALUES(99999999, 33333331, 0.0, 'PhD', 'Incomplete', FALSE);
INSERT INTO alumni VALUES(12345678, 2024, 'Masters');
INSERT INTO grad_secretary VALUES(12121212, NULL);
INSERT INTO admin VALUES(13131313, NULL);

-- Clear first
DELETE FROM transcript;
DELETE FROM schedule;

-- Now insert matching schedule
INSERT INTO schedule (course_id, semester, section, year, day, time_slot, instructor_id) VALUES
(1, 'Fall', 1, 2023, 'M', '15:00-17:30', 50000001),      -- SW Paradigms
(100, 'Fall', 1, 2023, 'T', '16:00-18:30', 22222222),    -- Computer Architecture
(101, 'Fall', 1, 2023, 'W', '15:00-17:30', 33333333),    -- Algorithms
(4, 'Fall', 1, 2023, 'R', '18:00-20:30', 50000001),      -- Machine Learning
(5, 'Fall', 1, 2023, 'F', '16:00-18:30', 50000002),      -- Networks 1

(6, 'Spring', 1, 2024, 'M', '15:00-17:30', 50000003),    -- Networks 2
(7, 'Fall', 1, 2024, 'T', '15:00-17:30', 50000004),      -- Database 1
(8, 'Fall', 1, 2024, 'W', '15:00-17:30', 50000004),      -- Database 2
(9, 'Fall', 1, 2024, 'R', '16:00-18:30', 50000005),      -- Compilers
(10, 'Fall', 1, 2024, 'F', '18:00-20:30', 50000005),     -- Multimedia

(11, 'Fall', 1, 2024, 'M', '15:00-17:30', 22222222),     -- Cloud Computing
(12, 'Spring', 1, 2024, 'T', '16:00-18:30', 50000002),   -- SW Engineering
(13, 'Fall', 1, 2024, 'W', '18:00-20:30', 50000003),     -- Graphics 1
(14, 'Fall', 1, 2024, 'R', '15:00-17:30', 50000004),     -- Security 1
(15, 'Fall', 1, 2024, 'F', '16:00-18:30', 50000005),     -- Cryptography

(16, 'Fall', 1, 2024, 'M', '18:00-20:30', 50000001),     -- Network Security
(17, 'Fall', 1, 2024, 'T', '15:00-17:30', 50000002),     -- Algorithms 2
(18, 'Fall', 1, 2024, 'W', '15:00-17:30', 50000003),     -- Embedded Systems
(19, 'Fall', 1, 2024, 'R', '16:00-18:30', 33333333);     -- Cryptography 2


-- Paul McCartney (UID: 55555555)
INSERT INTO transcript VALUES (55555555, 1, 1, 'Fall', 2023, 'A', TRUE);
INSERT INTO transcript VALUES (55555555, 100, 1, 'Fall', 2023, 'A', TRUE);
INSERT INTO transcript VALUES (55555555, 101, 1, 'Fall', 2023, 'A', TRUE);
INSERT INTO transcript VALUES (55555555, 5, 1, 'Fall', 2023, 'A', TRUE);
INSERT INTO transcript VALUES (55555555, 12, 1, 'Spring', 2024, 'A', TRUE);
INSERT INTO transcript VALUES (55555555, 6, 1, 'Spring', 2024, 'B', TRUE);
INSERT INTO transcript VALUES (55555555, 14, 1, 'Fall', 2024, 'B', TRUE);
INSERT INTO transcript VALUES (55555555, 8, 1, 'Fall', 2024, 'B', TRUE);
INSERT INTO transcript VALUES (55555555, 17, 1, 'Fall', 2024, 'B', TRUE);
INSERT INTO transcript VALUES (55555555, 13, 1, 'Fall', 2024, 'B', TRUE);

-- George Harrison (UID: 66666666)
INSERT INTO transcript VALUES (66666666, 4, 1, 'Fall', 2023, 'C', TRUE);
INSERT INTO transcript VALUES (66666666, 1, 1, 'Fall', 2023, 'B', TRUE);
INSERT INTO transcript VALUES (66666666, 100, 1, 'Fall', 2023, 'B', TRUE);
INSERT INTO transcript VALUES (66666666, 101, 1, 'Fall', 2023, 'B', TRUE);
INSERT INTO transcript VALUES (66666666, 5, 1, 'Fall', 2023, 'B', TRUE);
INSERT INTO transcript VALUES (66666666, 12, 1, 'Spring', 2024, 'B', TRUE);
INSERT INTO transcript VALUES (66666666, 6, 1, 'Spring', 2024, 'B', TRUE);
INSERT INTO transcript VALUES (66666666, 13, 1, 'Fall', 2024, 'B', TRUE);
INSERT INTO transcript VALUES (66666666, 17, 1, 'Fall', 2024, 'B', TRUE);
INSERT INTO transcript VALUES (66666666, 18, 1, 'Fall', 2024, 'B', TRUE);


-- Ringo Starr (UID: 99999999)
INSERT INTO transcript VALUES (99999999, 1, 1, 'Fall', 2023, 'A', TRUE);
INSERT INTO transcript VALUES (99999999, 100, 1, 'Fall', 2023, 'A', TRUE);
INSERT INTO transcript VALUES (99999999, 101, 1, 'Fall', 2023, 'A', TRUE);
INSERT INTO transcript VALUES (99999999, 4, 1, 'Fall', 2023, 'A', TRUE);
INSERT INTO transcript VALUES (99999999, 5, 1, 'Fall', 2023, 'A', TRUE);
INSERT INTO transcript VALUES (99999999, 6, 1, 'Spring', 2024, 'A', TRUE);
INSERT INTO transcript VALUES (99999999, 7, 1, 'Fall', 2024, 'A', TRUE);
INSERT INTO transcript VALUES (99999999, 8, 1, 'Fall', 2024, 'A', TRUE);
INSERT INTO transcript VALUES (99999999, 12, 1, 'Spring', 2024, 'A', TRUE);
INSERT INTO transcript VALUES (99999999, 13, 1, 'Fall', 2024, 'A', TRUE);
INSERT INTO transcript VALUES (99999999, 14, 1, 'Fall', 2024, 'A', TRUE);
INSERT INTO transcript VALUES (99999999, 15, 1, 'Fall', 2024, 'A', TRUE);

INSERT INTO user VALUES(00000001, 'Student', 'password', 'Chloe', 'Anderson', 8888, 'chloeanderson@email.com', 6666666667, 'Address', NULL);
INSERT INTO student VALUES(00000001, 33333331, 0.0, 'Masters', 'Incomplete', TRUE);