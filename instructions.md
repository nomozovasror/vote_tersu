# 🧭 Real-Time Voting System — Instructions

## 🎯 Project Goal
Create a **real-time voting system** using **FastAPI** (backend) and **React (Vite)** (frontend).  
Admins can manage events, start/stop voting sessions, and see live results.  
Users vote through a **generated unique link** within a limited time (default 15 seconds).  
Admins control the voting from their computer, while a **“display screen” page** shows the currently voting candidate with a large timer and information for audiences.

---

## 🧱 Stack
| Layer | Technology |
|--------|-------------|
| Backend | FastAPI + SQLAlchemy + Pydantic |
| Realtime | WebSocket (FastAPI built-in) |
| Auth | JWT (admin only) |
| Database | SQLite |
| Frontend | React + Vite + TypeScript |
| Styling | Tailwind CSS |
| Deployment | Docker & docker-compose |
| External API | `https://student.tersu.uz/rest/v1/data/employee-list` |
| Realtime Updates | WebSocket broadcast hub |

---

## 👤 User Roles
### 🧑‍💼 Admin
- Logs in with **username/password (JWT)**  
- Syncs candidate list from external API  
- Adds manual candidates if needed  
- Creates and starts events  
- Controls voting time (default 15s, editable)  
- Monitors real-time results  
- Controls the **display screen** (sets candidate and timer)

### 🙋 Voter
- Accesses a generated link (`/vote/<event_link>`)  
- Can vote **once per event** (IP + nonce check)  
- Votes via WebSocket connection  
- Sees real-time updates

### 📺 Display Screen
- Separate public page (`/display/<event_link>`)  
- Shows:
  - Current candidate (photo, name, position)
  - Large countdown timer
  - Optional vote counts (real-time)
- Controlled by admin

---

## 🧩 Backend (FastAPI)

### Main Features
1. **Admin Authentication**
   - `/auth/login` → returns JWT
   - `/auth/me` → verify token

2. **Candidates**
   - `/candidates/sync-from-api` → fetches from external API  
     Headers: `Authorization: Bearer <token>`  
   - `/candidates/manual` → manual candidate add  
   - `/candidates` → list  
   - `/candidates/{id}` → patch fields (`election_time`, `description`)

3. **Events**
   - `/events` (POST) → create event with candidates  
     - Generates `unique link`  
     - Default `duration_sec=15`
   - `/events/{id}/start` → start event  
   - `/events/{id}/stop` → stop event  
   - `/events/{id}/results` → get tally  
   - `/events/by-link/{link}` → get event metadata (public)

4. **Voting (WebSocket)**
   - `/ws/vote/{link}`
   - Receives:  
     ```json
     { "type": "cast_vote", "candidate_id": 5, "nonce": "uuid" }
     ```
   - Broadcasts:  
     ```json
     { "type": "tally", "candidate_id": 5, "votes": 10, "percent": 45.5 }
     ```
   - Prevents duplicate votes (IP + nonce)

5. **Display Screen (WebSocket)**
   - `/ws/display/{link}`
   - Admin control:
     - `POST /display/{event_id}/set-current`
       ```json
       { "candidate_id": 12, "countdown_sec": 15 }
       ```
   - Broadcast:
     ```json
     { "type": "display_update", "candidate": {...}, "remaining_ms": 12000 }
     ```

6. **Admin Dashboard**
   - `/admin/events` → list events  
   - `/admin/events/{id}` → event detail  
   - `/admin/events/{id}/live-tally` → real-time results  

---

## 🗄️ Database Models (SQLAlchemy)

### AdminUser
| Field | Type | Description |
|--------|------|-------------|
| id | int | PK |
| username | str | unique |
| password_hash | str | bcrypt |
| is_active | bool | default True |

### Candidate
| Field | Type |
|--------|------|
| id | int |
| full_name | str |
| image | str |
| birth_date | date |
| degree | str |
| position | str |
| election_time | datetime |
| description | str |
| from_api | bool |
| external_id | int? |

### Event
| Field | Type |
|--------|------|
| id | int |
| name | str |
| link | str (uuid) |
| duration_sec | int |
| status | Enum(pending, active, finished) |
| start_time | datetime |
| end_time | datetime |

### Vote
| Field | Type |
|--------|------|
| id | int |
| event_id | FK |
| candidate_id | FK |
| ip_address | str |
| timestamp | datetime |

### DisplayState
| Field | Type |
|--------|------|
| id | int |
| event_id | FK |
| current_candidate_id | FK |
| countdown_until | datetime |

---

## 🌐 Frontend (React + Vite)

### Routes
| Path | Description |
|------|--------------|
| `/admin/login` | Admin login |
| `/admin/dashboard` | Overview, create event |
| `/admin/event/:id` | Live tally, start/stop, display control |
| `/vote/:link` | Public voting page |
| `/display/:link` | Public “large screen” display |

### Components
- **CandidateCard.tsx** — candidate info and vote button  
- **TimerBig.tsx** — large countdown (display page)  
- **TallyBars.tsx** — bar chart for live votes  
- **DisplayPage.tsx** — fullscreen timer + candidate info  

### UI Requirements
- **Display page:**  
  - Large font, dark background  
  - Full-screen toggle  
  - Live countdown and candidate info  
- **Admin dashboard:**  
  - Table of events, start/stop controls  
  - “Copy Vote Link” button  
  - “Set Display Candidate” control  
- **Vote page:**  
  - Candidate cards with “Vote” button  
  - Once voted → disabled  
  - Real-time bar chart  

---

## ⏱️ Timing Logic
- Event starts: `start_time` recorded, timer = `duration_sec`
- Display timer set by admin (`countdown_sec`)
- Display timer can end independently of event timer
- Optionally: auto-stop when display timer = 0

---

## 🐳 Docker Setup

### docker-compose.yml
```yaml
version: '3.12'
services:
  api:
    build: ./api
    container_name: voting_api
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
  web:
    build: ./web
    container_name: voting_web
    ports:
      - "5173:80"
