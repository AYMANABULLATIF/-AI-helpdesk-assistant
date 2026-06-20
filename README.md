# AI Helpdesk Support Assistant

A portfolio-ready Streamlit application that demonstrates Tier-1 IT helpdesk workflows, AI-assisted ticket triage, and a small local RAG-style knowledge base assistant.

The project is intentionally scoped as a practical MVP that can be completed and explained in 1-2 days. It focuses on realistic support scenarios instead of overengineered infrastructure.

## Why This Project Is Relevant to IT Helpdesk / IT Support

Helpdesk technicians regularly classify tickets, identify priority, communicate professionally with users, and search internal documentation for troubleshooting steps. This project demonstrates those skills in a modern AI-assisted workflow:

- Converts plain-language user issues into structured ticket triage fields.
- Suggests first troubleshooting steps based on common Tier-1 support practices.
- Searches a local IT knowledge base for relevant procedures.
- Produces professional first-response messages suitable for a service desk environment.
- Shows awareness of escalation paths for Network, Desktop Support, Messaging, IAM, and Security teams.

## Features

### Ticket Triage

Users can enter an IT support issue such as:

- "I cannot connect to the VPN from home."
- "My laptop is very slow and keeps freezing."
- "I cannot access my company email."
- "The printer is not working and I need it urgently."

The app returns:

- Category: Network, Hardware, Software, Email, Account, Printer, Security, or Other
- Priority: Low, Medium, High, or Critical
- Sentiment: Calm, Frustrated, Angry, or Urgent
- Suggested department or resolver team
- First troubleshooting steps
- A short professional first-response message

### Knowledge Base Search

The app includes a local `knowledge_base/` folder with realistic sample documents for:

- VPN troubleshooting
- Printer troubleshooting
- Windows slow PC checklist
- Email login issues
- Password reset and account lockout
- Basic network troubleshooting

Technicians can ask questions such as:

> How do I troubleshoot VPN connection failure?

The app retrieves relevant knowledge base content with a simple local keyword search and generates an answer grounded in the available documents.

### Local Fallback Mode

If a Gemini API key is not configured, the app still runs using a local rule-based fallback. This makes the project easy to demo during interviews or on a resume without exposing API keys.

## Tech Stack

- Python
- Streamlit
- Google Gemini API through `google-generativeai`
- Local keyword-based knowledge base search
- Markdown, text, and PDF knowledge base loading
- python-dotenv for environment variables

The LLM provider is isolated behind a small provider class, so Gemini can be replaced later with OpenAI or another provider without rewriting the Streamlit UI. The knowledge base search is intentionally dependency-light for easier Windows setup.

## Project Structure

```text
AI Helpdesk Support Assistant
|-- app.py
|-- requirements.txt
|-- .env.example
|-- README.md
|-- screenshots/
|   `-- .gitkeep
`-- knowledge_base/
    |-- basic_network_troubleshooting.md
    |-- email_login_issues.md
    |-- password_reset_account_lockout.md
    |-- printer_troubleshooting.md
    |-- vpn_troubleshooting.md
    `-- windows_slow_pc_checklist.md
```

## How to Run Locally on Windows

### 1. Clone or open the project folder

Open PowerShell in the project directory.

### 2. Create a virtual environment

```powershell
python -m venv .venv
```

### 3. Activate the virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation scripts, run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate the virtual environment again.

### 4. Install dependencies

```powershell
pip install -r requirements.txt
```

### 5. Configure the Gemini API key

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and add your Gemini API key:

```text
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash
```

If you do not add an API key, the app will still run in local fallback mode.

### 6. Start the Streamlit app

```powershell
streamlit run app.py
```

Open the local URL shown in the terminal, usually:

```text
http://localhost:8501
```

## Streamlit Community Cloud Deployment

This app is ready for Streamlit Community Cloud. A local `.env` file is not required in deployment.

1. Push the project to a GitHub repository.
2. In Streamlit Community Cloud, create a new app from the repository.
3. Set the main file path to `app.py`.
4. Add your Gemini key in Streamlit app secrets:

```toml
GEMINI_API_KEY = "your_gemini_api_key_here"
GEMINI_MODEL = "gemini-1.5-flash"
```

Do not commit `.env` or `.streamlit/secrets.toml` to GitHub. Both are ignored by `.gitignore`.

## Example Ticket Outputs

### Example 1

Input:

```text
I cannot connect to the VPN from home.
```

Expected output style:

```text
Category: Network
Priority: Medium
Sentiment: Calm
Suggested team: Network Support
First steps:
- Confirm the user has working internet access.
- Verify the VPN client and profile.
- Check username, password, and MFA prompt.
```

### Example 2

Input:

```text
The printer is not working and I need it urgently.
```

Expected output style:

```text
Category: Printer
Priority: High
Sentiment: Urgent
Suggested team: Desktop Support
First steps:
- Confirm printer name and location.
- Check printer power, paper, toner, and queue status.
- Ask whether other users are affected.
```

### Example 3

Input:

```text
I cannot access my company email.
```

Expected output style:

```text
Category: Email
Priority: Medium
Sentiment: Calm
Suggested team: Messaging / Email Support
First steps:
- Check whether webmail works.
- Verify password, MFA, and account status.
- Check for email service health alerts.
```

## Resume Bullet Points

- Built a Python and Streamlit helpdesk assistant that triages IT support tickets by category, priority, user sentiment, resolver team, and first troubleshooting steps.
- Created a local IT knowledge base search workflow using sample Tier-1 support documentation for VPN, printer, email, account, Windows, and network issues.
- Designed a practical support workflow that demonstrates ticket intake, user communication, troubleshooting documentation, and escalation awareness for entry-level IT support roles.

## Future Improvements

- Add ticket export to CSV or SQLite.
- Add authentication for technician users.
- Add OpenAI as a second provider option.
- Add file upload controls for new IT policies or SOPs.
- Add service-level agreement timers and ticket status tracking.
- Add admin controls for updating categories, priority rules, and resolver groups.
- Add screenshots and a short demo video after the app is running locally.

## Notes

This project is for learning and portfolio demonstration. In a production helpdesk environment, ticket triage and password or MFA workflows should follow company security policies, audit requirements, and approval processes.
