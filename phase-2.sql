PRAGMA foreign_keys=OFF;

-- Drop all tables
DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS application;
DROP TABLE IF EXISTS academicInformation;
DROP TABLE IF EXISTS priorDegree;
DROP TABLE IF EXISTS recommendationLetter;
DROP TABLE IF EXISTS reviewForm;
DROP TABLE IF EXISTS student;
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

CREATE TABLE faculty (
  UID             INTEGER not null PRIMARY KEY,
  dept            VARCHAR(50) not null,
  FOREIGN KEY (UID) REFERENCES user(UID)
);

CREATE TABLE student (
  UID             INTEGER not null PRIMARY KEY,
  advisor_id      INTEGER,
  GPA             DECIMAL,
  program   VARCHAR(50) CHECK (program IN ('Masters', 'PhD')),
  thesis_status   VARCHAR(50) CHECK (program IN ('Complete', 'Incomplete', NULL)), 
  FOREIGN KEY (UID) REFERENCES user(UID),
  FOREIGN KEY (advisor_id) REFERENCES faculty(UID)
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
  degree       VARCHAR(50) CHECK (degree IN ('Masters', 'PhD')),
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
    student_uid INT,
    course_id INT,
    section INT,
    semester VARCHAR(20),
    year INT,
    grade VARCHAR(2) CHECK (grade IN ('A','A-','B+','B','B-','C+','C','F','IP')),
    graded BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (student_uid, course_id, section, semester),
    FOREIGN KEY (student_uid) REFERENCES student(UID),
    FOREIGN KEY (course_id, section, semester, year) REFERENCES schedule(course_id, section, semester, year)
);

-- Application status tracking with application date
CREATE TABLE application (
    UID                     INTEGER not null PRIMARY KEY,
    applicationStatus       varchar(50) not null CHECK (applicationStatus IN ('Incomplete', 'Complete and Under Review','Reviewed', 'Admitted', 'Rejected')),
    applySemester           varchar(10) not null CHECK (applySemester IN ('Fall', 'Spring')),
    applyYear               varchar(4) not null,
    decisionType            varchar(20) CHECK (decisionType IN ('Admit with Aid', 'Admit without Aid', 'Reject', NULL)),
    recommendedAdvisor      varchar(100),
    deficiencycourse       TEXT,
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

-- Faculty review form with GAS rating system
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
  foreign key (UID) references student(UID)
);

CREATE TABLE form1 (
  form1_id         INTEGER not null PRIMARY KEY,
  UID              INTEGER not null,
  status           VARCHAR(50) not null CHECK (status IN ('Submitted', 'Approved', 'Rejected')),
  foreign key (UID) references student(UID)
);

CREATE TABLE form1_course (
  form1_id         INTEGER not null,
  course_id        INTEGER not null,
  primary key (form1_id, course_id),
  foreign key (form1_id) references form1(form1_id),
  foreign key (course_id) references course(course_id)
);


INSERT INTO course VALUES (1, 'CSCI', 6221, 'SW Paradigms', 3, NULL);
INSERT INTO course VALUES (2, 'CSCI', 6461, 'Computer Architecture', 3, NULL);
INSERT INTO course VALUES (3, 'CSCI', 6212, 'Algorithms', 3, NULL);
INSERT INTO course VALUES (4, 'CSCI', 6220, 'Machine Learning', 3, NULL);
INSERT INTO course VALUES (5, 'CSCI', 6232, 'Networks 1', 3, NULL);
INSERT INTO course VALUES (6, 'CSCI', 6241, 'Database 1', 3, NULL);
INSERT INTO course VALUES (7, 'CSCI', 6260, 'Multimedia', 3, NULL);
INSERT INTO course VALUES (8, 'CSCI', 6262, 'Graphics 1', 3, NULL);
INSERT INTO course VALUES (9, 'ECE', 6241, 'Communication Theory', 3, NULL);
INSERT INTO course VALUES (10, 'ECE', 6242, 'Information Theory', 2, NULL);
INSERT INTO course VALUES (11, 'MATH', 6210, 'Logic', 2, NULL);
INSERT INTO course VALUES (12, 'CSCI', 6233, 'Networks 2', 3, NULL);
INSERT INTO course VALUES (13, 'CSCI', 6242, 'Database 2', 3, NULL);
INSERT INTO course VALUES (14, 'CSCI', 6246, 'Compilers', 3, NULL);
INSERT INTO course VALUES (15, 'CSCI', 6251, 'Cloud Computing', 3, NULL);
INSERT INTO course VALUES (16, 'CSCI', 6254, 'SW Engineering', 3, NULL);
INSERT INTO course VALUES (17, 'CSCI', 6283, 'Security 1', 3, NULL);
INSERT INTO course VALUES (18, 'CSCI', 6284, 'Cryptography', 3, NULL);
INSERT INTO course VALUES (19, 'CSCI', 6286, 'Network Security', 3, NULL);
INSERT INTO course VALUES (20, 'CSCI', 6325, 'Algorithms 2', 3, NULL);
INSERT INTO course VALUES (21, 'CSCI', 6339, 'Embedded Systems', 3, NULL);
INSERT INTO course VALUES (22, 'CSCI', 6384, 'Cryptography 2', 3, NULL);

INSERT INTO user VALUES(55555555, 'Student', 'password', 'Paul', 'McCartney', 1111, 'paulmccartney@email.com', 12345678, 'Address', NULL);
INSERT INTO user VALUES(66666666, 'Student', 'password', 'George', 'Harrison', 2222, 'georgeharrison@email.com', 87654321, 'Address', NULL);
INSERT INTO user VALUES(99999999, 'Student', 'password', 'Ringo', 'Starr', 3333, 'ringostarr@email.com', 1111111111, 'Address', NULL);
INSERT INTO user VALUES(12345678, 'Alumni', 'password', 'Eric', 'Clapton', 4444, 'ericclapton@email.com', 222222222, 'Address', NULL);
INSERT INTO user VALUES(12121212, 'GS', 'password', 'John', 'Snow', 5555, 'johnsnow@email.com', 3333333333, 'Address', NULL);
INSERT INTO user VALUES(22222222, 'Faculty', 'password', 'Bhagirath', 'Narahari', 6666, 'bnarahari@email.com', 4444444444, 'Address', NULL);
INSERT INTO user VALUES(33333333, 'Faculty', 'password', 'Gabe', 'Parmer', 7777, 'gparmer@email.com', 5555555555, 'Address', NULL);
INSERT INTO user VALUES(13131313, 'Admin', 'password', 'Jett', 'Jacobs', 8888, 'jettjacobs@email.com', 6666666666, 'Address', NULL);

INSERT INTO faculty VALUES(22222222, 'CSCI');
INSERT INTO faculty VALUES(33333333, 'CSCI');
INSERT INTO student VALUES(55555555, 22222222, 0.0, 'Masters', NULL);
INSERT INTO student VALUES(66666666, 22222222, 0.0, 'Masters', NULL);
INSERT INTO student VALUES(99999999, 33333333, 0.0, 'PhD', 'Incomplete');
INSERT INTO alumni VALUES(12345678, 2024, 'Masters');
INSERT INTO grad_secretary VALUES(12121212, NULL);
INSERT INTO admin VALUES(13131313, NULL);

-- First, clear any existing data to avoid conflicts
DELETE FROM transcript;
DELETE FROM schedule;

-- Fall 2023 Schedule Entries
INSERT INTO schedule VALUES (1, 'Fall', 1, 2023, 'M', '15:00-17:30', 22222222);
INSERT INTO schedule VALUES (2, 'Fall', 1, 2023, 'T', '16:00-18:30', 22222222);
INSERT INTO schedule VALUES (3, 'Fall', 1, 2023, 'W', '15:00-17:30', 22222222);
INSERT INTO schedule VALUES (4, 'Fall', 1, 2023, 'R', '18:00-20:30', 22222222);
INSERT INTO schedule VALUES (5, 'Fall', 1, 2023, 'F', '16:00-18:30', 22222222);
INSERT INTO schedule VALUES (7, 'Fall', 1, 2023, 'T', '16:00-18:30', 22222222);

-- Spring 2024 Schedule Entries
INSERT INTO schedule VALUES (6, 'Spring', 1, 2024, 'M', '15:00-17:30', 22222222);
INSERT INTO schedule VALUES (8, 'Fall', 1, 2024, 'W', '15:00-17:30', 22222222);
INSERT INTO schedule VALUES (10, 'Fall', 1, 2023, 'R', '18:00-20:30', 22222222);
INSERT INTO schedule VALUES (12, 'Spring', 1, 2024, 'F', '16:00-18:30', 22222222);
INSERT INTO schedule VALUES (13, 'Fall', 1, 2024, 'M', '15:00-17:30', 22222222);
INSERT INTO schedule VALUES (14, 'Spring', 1, 2024, 'T', '16:00-18:30', 22222222);
INSERT INTO schedule VALUES (15, 'Spring', 1, 2024, 'W', '15:00-17:30', 22222222);
INSERT INTO schedule VALUES (17, 'Fall', 1, 2024, 'R', '18:00-20:30', 22222222);
INSERT INTO schedule VALUES (18, 'Fall', 1, 2024, 'F', '16:00-18:30', 22222222);

-- Paul McCartney (UID: 55555555)
INSERT INTO transcript VALUES (55555555, 1, 1, 'Fall', 2023, 'A', TRUE);
INSERT INTO transcript VALUES (55555555, 2, 1, 'Fall', 2023, 'A', TRUE);
INSERT INTO transcript VALUES (55555555, 3, 1, 'Fall', 2023, 'A', TRUE);  
INSERT INTO transcript VALUES (55555555, 5, 1, 'Fall', 2023, 'A', TRUE);
INSERT INTO transcript VALUES (55555555, 12, 1, 'Spring', 2024, 'A', TRUE);
INSERT INTO transcript VALUES (55555555, 6, 1, 'Spring', 2024, 'B', TRUE);
INSERT INTO transcript VALUES (55555555, 14, 1, 'Spring', 2024, 'B', TRUE);
INSERT INTO transcript VALUES (55555555, 8, 1, 'Fall', 2024, 'B', TRUE);
INSERT INTO transcript VALUES (55555555, 17, 1, 'Fall', 2024, 'B', TRUE);
INSERT INTO transcript VALUES (55555555, 13, 1, 'Fall', 2024, 'B', TRUE);

-- George Harrison (UID: 66666666)
INSERT INTO transcript VALUES (66666666, 10, 1, 'Fall', 2023, 'C', TRUE);
INSERT INTO transcript VALUES (66666666, 1, 1, 'Fall', 2023, 'B', TRUE);
INSERT INTO transcript VALUES (66666666, 2, 1, 'Fall', 2023, 'B', TRUE);
INSERT INTO transcript VALUES (66666666, 3, 1, 'Fall', 2023, 'B', TRUE);
INSERT INTO transcript VALUES (66666666, 5, 1, 'Fall', 2023, 'B', TRUE);
INSERT INTO transcript VALUES (66666666, 12, 1, 'Spring', 2024, 'B', TRUE);
INSERT INTO transcript VALUES (66666666, 6, 1, 'Spring', 2024, 'B', TRUE);
INSERT INTO transcript VALUES (66666666, 13, 1, 'Fall', 2024, 'B', TRUE);  
INSERT INTO transcript VALUES (66666666, 17, 1, 'Fall', 2024, 'B', TRUE);
INSERT INTO transcript VALUES (66666666, 18, 1, 'Fall', 2024, 'B', TRUE);

-- Ringo Starr (UID: 99999999)
INSERT INTO transcript VALUES (99999999, 1, 1, 'Fall', 2023, 'A', TRUE);
INSERT INTO transcript VALUES (99999999, 2, 1, 'Fall', 2023, 'A', TRUE);
INSERT INTO transcript VALUES (99999999, 3, 1, 'Fall', 2023, 'A', TRUE);
INSERT INTO transcript VALUES (99999999, 4, 1, 'Fall', 2023, 'A', TRUE);
INSERT INTO transcript VALUES (99999999, 5, 1, 'Fall', 2023, 'A', TRUE);
INSERT INTO transcript VALUES (99999999, 6, 1, 'Spring', 2024, 'A', TRUE);
INSERT INTO transcript VALUES (99999999, 7, 1, 'Fall', 2023, 'A', TRUE);
INSERT INTO transcript VALUES (99999999, 8, 1, 'Fall', 2024, 'A', TRUE);
INSERT INTO transcript VALUES (99999999, 12, 1, 'Spring', 2024, 'A', TRUE);
INSERT INTO transcript VALUES (99999999, 13, 1, 'Fall', 2024, 'A', TRUE);
INSERT INTO transcript VALUES (99999999, 14, 1, 'Spring', 2024, 'A', TRUE);
INSERT INTO transcript VALUES (99999999, 15, 1, 'Spring', 2024, 'A', TRUE);