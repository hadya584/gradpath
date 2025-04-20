PRAGMA foreign_keys=OFF;

-- Drop all tables
DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS applicant;
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
  FOREIGN KEY (advisor_id) REFERENCES faculty(faculty_id)
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
    PRIMARY KEY (course_id, section, semester),
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