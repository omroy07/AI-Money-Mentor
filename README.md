<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:1a1a2e,50:16213e,100:0f3460&height=250&section=header&text=AI%20Money%20Mentor&fontSize=68&fontColor=e94560&fontAlignY=42&desc=Your%2024%2F7%20Intelligent%20Finance%20Companion&descSize=18&descAlignY=62&descColor=a8b2d8&animation=twinkling" width="100%"/>

<br/>

<a href="https://git.io/typing-svg"><img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=22&pause=1000&color=E94560&center=true&vCenter=true&width=600&lines=Track+Income+%26+Expenses+📊;AI-Powered+Budget+Planning+💡;Smart+Investment+Guidance+📈;24%2F7+Financial+AI+Assistant+🧠;Democratizing+Financial+Freedom+🚀" alt="Typing SVG" /></a>

<br/><br/>

<img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/Flask-2.x-000000?style=flat-square&logo=flask&logoColor=white"/>
<img src="https://img.shields.io/badge/Groq_AI-Powered-F55036?style=flat-square&logo=groq&logoColor=white"/>
<img src="https://img.shields.io/badge/License-MIT-22c55e?style=flat-square"/>
<img src="https://img.shields.io/badge/Status-Active-6C63FF?style=flat-square"/>
<img src="https://img.shields.io/github/stars/omroy07/AI-Money-Mentor?style=flat-square&color=FFD700"/>
<img src="https://img.shields.io/github/issues/omroy07/AI-Money-Mentor?style=flat-square&color=e94560&label=Issues"/>

</div>

---

<img align="right" width="340" src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png"/>

## 💡 Why AI Money Mentor?

> **95% of people have no financial plan.**  
> Financial advisors cost $200–$400/hour.  
> AI Money Mentor costs nothing and is always available.

A **24/7 AI-powered personal CFO** for everyone — students, professionals, and families alike. It thinks, plans, and advises so you don't have to guess with your money.

<br/>

---

## ✨ Features

<br/>

<table>
  <tr>
    <td align="center" width="150"><h3>🧠</h3><b>AI Chat</b><br/><sub>Ask anything in plain English. Get expert financial answers instantly.</sub></td>
    <td align="center" width="150"><h3>📊</h3><b>Expense Tracker</b><br/><sub>Log daily transactions with smart auto-categorization.</sub></td>
    <td align="center" width="150"><h3>💡</h3><b>Smart Budget</b><br/><sub>AI-generated monthly plans tailored to your goals.</sub></td>
    <td align="center" width="150"><h3>📈</h3><b>Investments</b><br/><sub>SIP, stocks & savings recs based on your risk profile.</sub></td>
  </tr>
  <tr>
    <td align="center" width="150"><h3>🧾</h3><b>Reports</b><br/><sub>Weekly & monthly analysis with visual spending trends.</sub></td>
    <td align="center" width="150"><h3>🔔</h3><b>Smart Alerts</b><br/><sub>Bill reminders & overspending notifications.</sub></td>
    <td align="center" width="150"><h3>🔐</h3><b>Privacy First</b><br/><sub>Encrypted, local-first. Your data stays yours.</sub></td>
    <td align="center" width="150"><h3>🌍</h3><b>Always On</b><br/><sub>No appointments. No closing hours. Ever.</sub></td>
  </tr>
</table>

<br/>

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AI MONEY MENTOR                      │
└─────────────────────────────────────────────────────────┘
         │
         ▼
  ┌──────────────┐    HTTP     ┌─────────────────┐
  │  Frontend    │ ──────────► │  Flask Backend  │
  │  HTML/CSS/JS │ ◄────────── │  Python Server  │
  └──────────────┘             └────────┬────────┘
                                        │
                          ┌─────────────┼────────────┐
                          ▼             ▼             ▼
                   ┌────────────┐ ┌──────────┐ ┌──────────┐
                   │  Groq AI   │ │  OpenAI  │ │ Database │
                   │    LLM     │ │   API    │ │  SQLite  │
                   └────────────┘ └──────────┘ └──────────┘
```

---

## ⚙️ Tech Stack

<div align="center">

| Layer | Technology |
|:------|:-----------|
| **Frontend** | ![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white) ![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat-square&logo=css3&logoColor=white) ![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black) |
| **Backend** | ![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) ![Flask](https://img.shields.io/badge/Flask-000000?style=flat-square&logo=flask&logoColor=white) |
| **AI Engine** | ![Groq](https://img.shields.io/badge/Groq-F55036?style=flat-square&logo=groq&logoColor=white) ![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat-square&logo=openai&logoColor=white) |
| **Database** | ![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white) ![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=flat-square&logo=mysql&logoColor=white) |

</div>

---

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/omroy07/AI-Money-Mentor.git
cd AI-Money-Mentor

# Virtual environment
python -m venv venv
source venv/bin/activate          # Linux/macOS
# venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Add your GROQ_API_KEY to .env

# Run
python app.py
# → http://localhost:5000
```

---

## 🧪 Testing

```bash
pytest                        # Full suite
pytest -v                     # Verbose
pytest tests/test_tax.py -v   # Specific file
pytest --cov=app tests/       # With coverage
```

---

## 📁 Project Structure

```
AI-Money-Mentor/
├── static/
│   ├── css/           ← Stylesheets
│   ├── js/            ← JavaScript
│   └── assets/        ← Images & icons
├── templates/         ← Jinja2 HTML
├── tests/
│   └── test_tax.py    ← Pytest suite
├── app.py             ← Flask entry point
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🗺️ Roadmap

| Status | Feature |
|:------:|:--------|
| ✅ | AI Chat Assistant |
| ✅ | Expense Tracker + Auto-Categorization |
| ✅ | Smart Budget Planner |
| ✅ | Investment Suggestions |
| ✅ | Financial Reports (Weekly/Monthly) |
| ✅ | Smart Alerts & Bill Reminders |
| 🚧 | Mobile App (Android & iOS) |
| 🚧 | Voice-Based AI Assistant |
| 🔜 | Multi-Language Support |
| 🔜 | Bank API Integration |
| 🔜 | Advanced Portfolio Tracker |
| 💡 | Multi-Agent AI System |
| 💡 | Tax Optimization Module |
| 💡 | Crypto & DeFi Dashboard |

---

## 🐛 Issues & Feedback

Found a bug or have a feature request? [Open an issue](https://github.com/omroy07/AI-Money-Mentor/issues) — contributions and feedback are always welcome!

<div align="center">
<a href="https://github.com/omroy07/AI-Money-Mentor/issues/new?template=bug_report.md">
  <img src="https://img.shields.io/badge/🐛_Report_a_Bug-e94560?style=for-the-badge"/>
</a>
&nbsp;
<a href="https://github.com/omroy07/AI-Money-Mentor/issues/new?template=feature_request.md">
  <img src="https://img.shields.io/badge/💡_Request_a_Feature-6C63FF?style=for-the-badge"/>
</a>
</div>

---

## 🤝 Contributing

```bash
# Fork → Branch → Commit → PR

git checkout -b feature/amazing-feature
git commit -m "✨ Add amazing feature"
git push origin feature/amazing-feature
# Open a Pull Request on GitHub
```

---

## 📊 Impact

<div align="center">

| 📉 Reduces Financial Illiteracy | 💰 Builds Saving Habits | 📈 Smarter Investments | 🧠 Accessible to All |
|:---:|:---:|:---:|:---:|

</div>

---

## 🏆 ELUSOC 2026

<div align="center">

<a href="https://edulinkup.dev/elusoc/profile/omroy07">
  <img src="https://img.shields.io/badge/🏅_ELUSOC_2026-Admin_Badge_Holder-FFD700?style=for-the-badge&labelColor=1a1a2e"/>
</a>

</div>

---

## 📜 License

MIT License © 2025 Om Roy — free to use, modify, and distribute.

---

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0f3460,50:16213e,100:1a1a2e&height=140&section=footer&text=⭐+Star+this+repo+if+it+helped!&fontSize=22&fontColor=e94560&fontAlignY=55&animation=twinkling" width="100%"/>

[![GitHub](https://img.shields.io/badge/github-omroy07-E94560?style=for-the-badge&logo=github)](https://github.com/omroy07)

*Made with ❤️ to democratize financial intelligence for everyone.*

</div>