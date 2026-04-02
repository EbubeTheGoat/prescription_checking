# Prescription Safety Checker
# It is used to check prescriptions and send the results to your email.

Prescription Safety Checker is a high-performance digital health platform designed to enhance medication safety and pharmaceutical integrity. Engineered for the 2026 healthcare landscape, this application provides an intelligent interface for drug interaction screening, dosage verification, and pharmaceutical authentication. By integrating automated clinical decision support, the tool helps healthcare providers and patients prevent adverse drug reactions (ADRs) and identify potential counterfeit medications. Whether used for e-pharmacy compliance or as a standalone clinical pharmacology resource, Prescription Checker leverages real-time data analytics to ensure that every prescription is safe, accurate, and fully aligned with NDPR and global health data standards.


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
