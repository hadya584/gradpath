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

CREATE TABLE student (
  UID             INTEGER not null PRIMARY KEY,
  advisor_id      INTEGER,
  GPA             DECIMAL,
  program   VARCHAR(50) CHECK (program IN ('Masters', 'PhD')),
  thesis_status   VARCHAR(50),
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
    FOREIGN KEY (student_uid) REFERENCES User(UID),
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
  foreign key (UID) references Student(UID)
);

CREATE TABLE form1 (
  form1_id         INTEGER not null PRIMARY KEY,
  UID              INTEGER not null,
  form_type        VARCHAR(50) not null CHECK (form_type IN ('Form1', 'Advising')),
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

-- Insert courses
INSERT INTO course (course_id, dept, course_num, title, credits, instructor_id) VALUES
(1, 'CSCI', '6221', 'SW Paradigms', 3, NULL),
(2, 'CSCI', '6461', 'Computer Architecture', 3, NULL),
(3, 'CSCI', '6212', 'Algorithms', 3, NULL),
(4, 'CSCI', '6220', 'Machine Learning', 3, NULL),
(5, 'CSCI', '6232', 'Networks 1', 3, NULL),
(6, 'CSCI', '6241', 'Database 1', 3, NULL),
(7, 'CSCI', '6260', 'Multimedia', 3, NULL),
(8, 'CSCI', '6262', 'Graphics 1', 3, NULL),
(9, 'ECE', '6241', 'Communication Theory', 3, NULL),
(10, 'ECE', '6242', 'Information Theory', 2, NULL),
(11, 'MATH', '6210', 'Logic', 2, NULL),
(12, 'CSCI', '6233', 'Networks 2', 3, NULL),
(13, 'CSCI', '6242', 'Database 2', 3, NULL),
(14, 'CSCI', '6246', 'Compilers', 3, NULL),
(15, 'CSCI', '6251', 'Cloud Computing', 3, NULL),
(16, 'CSCI', '6254', 'SW Engineering', 3, NULL),
(17, 'CSCI', '6283', 'Security 1', 3, NULL),
(18, 'CSCI', '6284', 'Cryptography', 3, NULL),
(19, 'CSCI', '6286', 'Network Security', 3, NULL),
(20, 'CSCI', '6325', 'Algorithms 2', 3, NULL),
(21, 'CSCI', '6339', 'Software Testing', 3, NULL); 


-- Insert faculty advisors
INSERT INTO user (UID, role, password, firstName, lastName, ssn, email, phone, address, address2)
VALUES
(11111111, 'Faculty', 'passNarahari', 'Narahari', 'Advisor', '111-11-1111', 'narahari@gwmail.gwu.edu', '123-456-7890', '123 Faculty St', NULL),
(22222222, 'Faculty', 'passParmer', 'Parmer', 'Advisor', '222-22-2222', 'parmer@gwmail.gwu.edu', '123-555-7890', '456 Faculty St', NULL);

INSERT INTO faculty (UID, dept) 
VALUES
(11111111, 'CSCI'),
(22222222, 'CSCI');

-- Insert grad secretary
INSERT INTO user (UID, role, password, firstName, lastName, ssn, email, phone, address, address2)
VALUES
(33333333, 'GS', 'passGS', 'Olivia', 'Secretary', '333-33-3333', 'olivia.secretary@gwmail.gwu.edu', '333-444-5555', '789 Admin St', NULL);

INSERT INTO grad_secretary (UID, office)
VALUES (33333333, 'Engineering Hall');

-- Insert students
INSERT INTO user (UID, role, password, firstName, lastName, ssn, email, phone, address, address2)
VALUES
(55555555, 'Student', 'passPaul', 'Paul', 'McCartney', '555-55-5555', 'paul.mccartney@gwmail.gwu.edu', '555-666-7777', '1 Beatles St', NULL),
(66666666, 'Student', 'passGeorge', 'George', 'Harrison', '666-66-6666', 'george.harrison@gwmail.gwu.edu', '666-777-8888', '2 Beatles St', NULL),
(88888888, 'Student', 'passRingo', 'Ringo', 'Starr', '888-88-8888', 'ringo.starr@gwmail.gwu.edu', '888-999-0000', '3 Beatles St', NULL);

INSERT INTO student (UID, advisor_id, GPA, program, thesis_status)
VALUES 
(55555555, 11111111, 3.5, 'Masters', NULL),
(66666666, 22222222, 3.2, 'Masters', NULL),
(88888888, 22222222, 4.0, 'PhD', 'Not Approved');

-- Insert alumni
INSERT INTO user (UID, role, password, firstName, lastName, ssn, email, phone, address, address2)
VALUES
(77777777, 'Alumni', 'passEric', 'Eric', 'Clapton', '777-77-7777', 'eric.clapton@gwmail.gwu.edu', '777-888-9999', '4 Music St', NULL);

INSERT INTO alumni (UID, grad_year, degree)
VALUES (77777777, 2014, 'Masters');

-- First, add the missing schedule entries for previous semesters
INSERT INTO schedule (course_id, semester, section, year, day, time_slot, instructor_id) VALUES
(1, 'Fall', 1, 2023, 'M', '15:00-17:30', NULL),
(2, 'Fall', 1, 2023, 'T', '16:00-18:30', NULL),
(3, 'Fall', 1, 2023, 'W', '18:00-20:30', NULL),
(5, 'Fall', 1, 2023, 'F', '16:00-18:30', NULL),
(12, 'Fall', 1, 2023, 'T', '18:00-20:30', NULL),
(6, 'Spring', 1, 2024, 'M', '18:00-20:30', NULL),
(8, 'Spring', 1, 2024, 'W', '16:00-18:30', NULL),
(13, 'Spring', 1, 2024, 'W', '15:00-17:30', NULL),
(14, 'Spring', 1, 2024, 'R', '16:00-18:30', NULL),
(17, 'Spring', 1, 2024, 'T', '16:00-18:30', NULL);

-- Then insert the transcripts
INSERT INTO transcript VALUES (55555555, 1, 1, 'Fall', 2023, 'A', TRUE);
INSERT INTO transcript VALUES (55555555, 3, 1, 'Fall', 2023, 'A', TRUE);
INSERT INTO transcript VALUES (55555555, 2, 1, 'Fall', 2023, 'A', TRUE);
INSERT INTO transcript VALUES (55555555, 5, 1, 'Fall', 2023, 'A', TRUE);
INSERT INTO transcript VALUES (55555555, 12, 1, 'Fall', 2023, 'A', TRUE);
INSERT INTO transcript VALUES (55555555, 6, 1, 'Spring', 2024, 'B', TRUE);
INSERT INTO transcript VALUES (55555555, 13, 1, 'Spring', 2024, 'B', TRUE);
INSERT INTO transcript VALUES (55555555, 14, 1, 'Spring', 2024, 'B', TRUE);
INSERT INTO transcript VALUES (55555555, 17, 1, 'Spring', 2024, 'B', TRUE);
INSERT INTO transcript VALUES (55555555, 8, 1, 'Spring', 2024, 'B', TRUE);
