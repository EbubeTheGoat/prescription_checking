# Prescription Safety Checker
It is used to check prescriptions and send the results to your email.

Prescriber Safety Checker is a robust healthcare technology application engineered to automate and secure the medical provider verification process. Designed for pharmacy informatics and clinical administrative workflows, the platform facilitates real-time credential validation, ensuring strict adherence to regulatory compliance and HIPAA security standards. By leveraging data-driven analytics and a scalable digital health architecture, this tool mitigates prescription fraud and enhances patient safety through precise National Provider Identifier (NPI) lookups and sanction monitoring. Whether integrated into an Electronic Health Record (EHR) ecosystem or used as a standalone clinical decision support tool, Prescriber Checker optimizes the integrity of the medication fulfillment cycle.


![github readme](https://github.com/user-attachments/assets/5f0493c3-5ed6-4d45-bd7f-eedf3b3eb9ca)

Installation & Setup
This project follows a decoupled architecture. This repository contains the Backend API, while the user interface is managed in a separate repository.

1. Prerequisites
Node.js (v18.0 or higher)
API Keys: Openai or any other ones

3. Backend Setup (This Repo)
First, clone the repository and install the server-side dependencies:

3. Environment Variables
Create a .env file in the root directory and add your configuration:

4. Running the Server( In this situation, I used Render)
   
5. Frontend Setup
To run the full application, you must also set up the client-side interface.
Go to the Frontend Repo: Prescriber Checker Frontend →https://github.com/EbubeTheGoat/prescription_checking2.git
Follow the installation instructions in that repository's README.md.
Ensure your Frontend .env points to the Backend URL (http://localhost:5000).

6. Run your Server (In the situation, i used Vercel)
7. Known Issues:
   a. High latency
   b. Only one page for uploading
   c. Problems with extracting the image

Solutions coming soon
