# Phase-2

## **DB Design**
<img width="727" alt="Screenshot 2025-05-03 at 8 46 08 PM" src="https://github.com/user-attachments/assets/931a5976-1c3b-4093-8ecf-ad90a5d6d060" />

### **Our DB was in 3NF for the following reasons:**

#### 1NF:
- All tables have a primary key.
- There are no repeating groups.
- Each column has atomic values.

#### 2NF:
- Meets 1NF.
- Non-key attributes are fully dependent on the primary key, thus there are no partial dependencies.

#### 3NF:
- Meets 2NF.
- There are no transitive dependencies between non-key attributes.

---

## **Visual Overview**
Include screenshots, an animated gif, or short video showing a feature from each component included in your project (e.g., APPS, REGs, ADV). It does not need to be an exhaustive video of your functionality, just enough to remind us of how it works/looks.

---

## **Design Justification**
For Integration Projects, this should focus on how you connected your components together. For Builder Projects, it should justify your key design decisions. *(0.5 - 1 page)*

Our team did an integration project. We started by creating a database that merged all information from each of our phase 1 group schemas. We then broke off and made each of our phase 1 modules work with the new merged schema. We then met up again and fixed redirections so that it was possible to go from the GS pages in APPS to the GS pages in REGS and to the GS pages in ADS, similarly for every role. From there, we focused on matriculation and graduation processes to let a user go from an applicant in APPS to a student in REGS to an alumni in ADS. After our modules were made into one working project, we broke off features, queries, and styling to make a polished and coherent project that was easy to use and performed as expected by the specifications.

---

## **Special Features**
~2 sentences describing each extra feature you added beyond the spec.

- We made a fun and happy-looking accept page for when an applicant got accepted by the university, which consisted of a dancing cat GIF, music, and confetti.  
- We also made a rejected screen for when the applicant got rejected from the university, which consisted of rain in the background, a loud buzzer noise, and a grayed-out screen.  
- The same sort of screen was used for when a user was put on academic suspension due to having 2 grades below a B. This also consisted of a grayed-out screen, rain, and a loud buzzer. This screen, however, had different text than the rejected one.

---

## **Work Breakdown**
List teammates and specify the aspects of the project they worked on:

- **Cole**: Worked mainly on APPS and applicant-related queries, as well as integrating the APPS module into the fully integrated project. He also helped style pages to make the project look like one coherent project instead of three distinct modules mashed together.  
- **Hadya**: Worked mainly on REGS and registration-related queries, as well as integrating the REGS module into the fully integrated project. She also helped style pages to make the project coherent.  
- **Sydney**: Worked mainly on ADS and advising/graduation-related queries, as well as integrating the ADS module into the fully integrated project. She also helped style pages to make the project coherent.  

All in all, we all worked mainly on our phase 1 assigned modules as we knew those parts the best, but we all worked together to help each other out with anything anyone was stuck on, and we all styled the many pages we had to make the transition from module to module seamless.

---

## **Report Deadline**
Your report is due by **11:59pm May 3rd** (earlier if possible!).
