# Installation and Run Guide (from zero, Windows 11)

You do not need to know programming for this guide. Every step says exactly what to click or type.
Time needed: about 15 minutes, most of it waiting for downloads.

## What you will end up with

A website that runs **on your own laptop** at `http://localhost:8000`. Nothing is put on the internet. Only you can open it.

## Step 1. Install Python (one time)

Python is the engine that runs the Voxora server.

1. Open https://www.python.org/downloads/ in your browser.
2. Click the big yellow button **Download Python 3.12.x** (any 3.10 or newer works).
3. Open the downloaded file. On the **first screen**, tick the box **"Add python.exe to PATH"** at the bottom. This is the step people miss.
4. Click **Install Now**. Wait. Click **Close**.
5. Check it worked: press the **Windows key**, type `cmd`, press Enter. In the black window type `python --version` and press Enter. You should see something like `Python 3.12.4`.
   If you see "Python was not found", reinstall and make sure the PATH box is ticked.

## Step 2. Unzip the project

1. Right-click `Voxora-AI-Complete-Project.zip` and choose **Extract All...**
2. Pick a short, simple place such as `C:\Voxora`. Click **Extract**.
   Avoid folders inside OneDrive if you can. Syncing can slow the database.
3. Open the extracted folder. You should see `setup.bat`, `run.bat`, `backend`, `frontend` and `docs`.

## Step 3. Install the project (one time)

1. Double-click **setup.bat**.
2. If Windows shows a blue "Windows protected your PC" box, click **More info**, then **Run anyway**. The file is a plain text script you can open in Notepad to read.
3. A black window appears and installs the packages. This takes 1 to 3 minutes. Wait for: **"Setup finished. Now double-click run.bat"**.
4. Press any key to close the window.

## Step 4. Start Voxora

1. Double-click **run.bat**.
2. A black window opens and stays open. This is the server. **Do not close it while you use the app.**
3. After a few seconds your browser opens `http://localhost:8000`. If it does not, open Chrome or Edge and type that address yourself.

The first start also creates the database and demo data. It takes a few seconds.

## Step 5. Sign in and look around

On the sign-in page, click one of the demo logins (it fills the form) and press **Sign in**.

| Login | Email | Password | What you see |
|---|---|---|---|
| Super Admin | admin@voxora.local | ChangeMe@123 | All companies. Create companies and logins. Open any company. |
| Skyline Realty | demo.realty@voxora.local | Demo@12345 | Real estate client dashboard |
| CityCare Hospital | demo.hospital@voxora.local | Demo@12345 | Healthcare client dashboard |
| BrightPath Academy | demo.academy@voxora.local | Demo@12345 | Education client dashboard |
| Skyline viewer | viewer.realty@voxora.local | Demo@12345 | Same company, view-only |

Things to try:

- As **Super Admin**: Companies, then **Open** on a company. A yellow bar reminds you that you are viewing as admin. Click **Back to companies** to leave.
- As a **client**: Dashboard, Calls (click a row to read the transcript), Records, Knowledge base, Plan and usage.
- Sign in as Skyline Realty, then as CityCare. Each sees only its own data. That is the privacy rule at the heart of the product.

## Step 6. Make your first test call

1. Sign in as a client (for example Skyline Realty). Open **Voice Studio**.
2. Use **Google Chrome or Microsoft Edge**. Other browsers often cannot listen.
3. Pick an agent and click **Start call**. The agent greets you out loud.
4. Click **Allow** when the browser asks to use your microphone.
5. Answer the agent's questions by speaking, or type in the box under the orb.
6. Watch the **Captured details** panel fill in. When the agent finishes (or you click **End call**), the call is saved. Click **Open full call** to see the transcript and summary.

Tips: Chrome's speech recognition needs the internet. If an agent speaks Hindi or Gujarati but you hear odd sounds, your computer has no voice for that language. Install one in **Windows Settings, Time and language, Speech**, or switch on Sarvam (below).

## Step 7 (optional). Turn on Gemini and Sarvam

Out of the box, a built-in free agent answers and your browser does the speech. To use the real AI services:

1. **Gemini key**: open https://aistudio.google.com, sign in with Google, click **Get API key**, then **Create API key**. Copy it.
2. **Sarvam key**: sign up at https://www.sarvam.ai, open the dashboard and create an API key. Check their site for the current free credits.
3. Open the folder `backend`, find the file named `.env`. If you cannot see it, in File Explorer click **View, Show, Hidden items**. Right-click it, **Open with, Notepad**.
4. Change these lines (paste your keys after the equals sign, no spaces, no quotes):

```
LLM_PROVIDER=gemini
GEMINI_API_KEY=paste-your-key-here
STT_PROVIDER=sarvam
TTS_PROVIDER=sarvam
SARVAM_API_KEY=paste-your-key-here
```

5. Save. Close the black server window, then double-click **run.bat** again.
6. Open Voice Studio. The panel **How this call runs** now says which services are active. If a key is missing or wrong, it tells you and falls back to the free mode.

Good to know: Google may use free-tier prompts to improve its products, so never test with real patient or customer data. Free tiers have rate limits; if Gemini says the limit is reached, wait a minute or set `LLM_PROVIDER=mock`.

## Stopping, restarting, resetting

- **Stop**: close the black server window (or press Ctrl+C in it).
- **Start again**: double-click run.bat. Your data is kept.
- **Back to fresh demo data**: stop the server, delete `backend\data\voxora.db`, start again.
- **Start with an empty system (no demo companies)**: set `SEED_DEMO=false` in `.env`, delete `backend\data\voxora.db`, start again. Then sign in as the Super Admin and create your first company.
- **Run the self-check**: double-click **test.bat**. You should see `OK` at the end. With the server running, you can also open a second Command Prompt in the `backend` folder and run `.venv\Scripts\python scripts\smoke_test.py`.

## Troubleshooting

| What you see | What to do |
|---|---|
| "Python was not found" | Reinstall Python and tick **Add python.exe to PATH**. Close and reopen setup.bat. |
| setup.bat fails during `pip install` | Check your internet connection and run setup.bat again. A company firewall can block downloads; try another network. |
| run.bat says "Please double-click setup.bat first" | Run setup.bat once. |
| "address already in use" or port 8000 busy | Another program uses port 8000. Close it, or edit run.bat and change both `8000` to `8001`, then open http://localhost:8001. |
| Browser shows "This site can't be reached" | The server window is closed or still starting. Start run.bat and wait 5 seconds. |
| Sign-in says "Too many failed attempts" | Wait 10 minutes, or restart the server. |
| The orb stays grey and nothing is heard | Use Chrome or Edge. Click the padlock in the address bar and allow the microphone. Or type your message in the box. |
| Agent speaks in a strange voice for Hindi or Gujarati | No voice for that language is installed. Install one in Windows Speech settings, or use Sarvam. |
| "Gemini model ... was not found" | Model names change. In Google AI Studio copy a current model name into `GEMINI_MODEL` in `.env`. |
| "Gemini free-tier limit reached" | Wait a minute, or set `LLM_PROVIDER=mock`. The call keeps working with the built-in agent. |
| "Sarvam rejected the API key" | Check `SARVAM_API_KEY` for extra spaces. Create a new key if needed. |
| Changed `.env` but nothing changed | Close the server window and start run.bat again. Settings load only at start. |
| Anything else | Copy the last lines from the black server window and use them in your question to a developer or an AI assistant, together with docs/CONTINUE_WITH_AI.md. |

## Doing it by hand (if you prefer typing commands)

Open Command Prompt in the `backend` folder:

```
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Mac or Linux: run `./setup.sh` then `./run.sh`. The interactive API documentation is at http://localhost:8000/docs while the server runs.
