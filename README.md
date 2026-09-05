# NEXUS — Flask gaming platform

An immersive gaming platform built with Python/Flask and a futuristic dark gaming frontend.

## Run locally on macOS

```bash
cd nexus-flask
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## Included

- Retro-futuristic neon design on a dark background
- CSS-built 3D hero core and floating scene
- Motion entrance, scroll, carousel, and ambient animations
- Interactive game showcase carousel with autoplay and controls
- Community, events, and download sections
- Trailer modal with Escape-key support
- Flask contact and download API endpoints
- JSON health check and games endpoint

Flask is the backend and template renderer. Player pages reuse the same NEXUS design tokens and load one shared `static/js/main.js` plus one page-specific script.

## Module 1: Player Command Center and Neon Runner

The active Module 1 flow adds a protected player command center and the first
playable experience without changing the existing landing page or authentication
model:

- `/dashboard` — player level, XP, login streak, daily reward, activity, library, and leaderboard preview.
- `/play/neon-runner` — a keyboard- and touch-friendly browser game.
- `/api/play/neon-runner/start` — creates a short-lived server-tracked run session.
- `/api/play/neon-runner/score` — accepts one score for a valid session and applies limited XP.
- `/api/daily-reward` — idempotent once-per-UTC-day reward claim.
- `/api/leaderboard?game=neon-runner` — verified completed runs only.

Scores are checked against the player session and elapsed time. This is a
practical abuse check for a browser game, not a claim of perfect anti-cheat.

### Database migration

The application no longer runs `db.create_all()` automatically in production.
After installing requirements and configuring `DATABASE_URL`, apply the safe
schema migration:

```bash
FLASK_APP=app flask db upgrade
```

The migration adds progression columns to the existing user table and creates
activity/play-session tables. It does not delete, reset, or recreate users.

For a disposable local database only, `NEXUS_AUTO_CREATE_DB=1` can be used;
production should always use `flask db upgrade`.

### Render start command

Run the migration before Gunicorn starts:

```bash
flask db upgrade && gunicorn --bind 0.0.0.0:$PORT app:app
```

Keep `SECRET_KEY`, `DATABASE_URL`, `TURNSTILE_SECRET_KEY`, `TURNSTILE_SITE_KEY`,
`GOOGLE_CLIENT_ID`, and `GOOGLE_CLIENT_SECRET` in Render environment variables.

## Game Radar and My Game Vault

The next approved module adds a focused discovery and collection experience while
leaving the original `/api/games` response unchanged:

- `/games` — searchable, filterable, sortable catalog with pagination.
- `/games/<slug>` — game details, related signals, aggregate ratings, and reviews.
- `/api/radar/games` and `/api/games/<slug>` — discovery JSON endpoints.
- `/api/games/<slug>/favorite` — idempotent save/remove actions for signed-in players.
- `/api/library` — saved games and recently played summaries for the dashboard.
- `/api/games/<slug>/review` — one validated review per signed-in player and game.

The catalog is server-owned for this module. Only the existing Neon Runner is
playable; game uploads, social posts, tournaments, payments, and admin tooling
remain intentionally out of scope.

The `20260905_game_radar` migration creates only the new favorites, reviews, and
recent-play tables. It preserves existing users, progression, sessions, and game
data. Apply it with the same Render start command or with:

```bash
FLASK_APP=app flask db upgrade
```
Yes — here is a polished **project booklet / web-app resume** for **NEXUS — Play the Edge**. You can paste it into your GitHub `README.md`, portfolio, college project report, LinkedIn project section, or convert it into a PDF later.

Your project is a Flask-based gaming platform with secure authentication, Google OAuth, Cloudflare Turnstile protection, games, community, events, downloads, and a futuristic dark UI. The Phase 1 work should focus only on stabilizing signup, Turnstile, CSRF, profiles, password recovery, and email verification—not later gameplay or monetization features. [github](https://github.com/openai/skills/blob/main/skills/.curated/security-best-practices/references/python-flask-web-server-security.md)

# NEXUS — Play the Edge

> **Play the Edge. Own the Arena.**

A futuristic gaming platform built to bring together game discovery, player identity, competitive events, and community interaction in one immersive digital space.

***

## Project Overview

**NEXUS — Play the Edge** is a full-stack gaming web application built using Python and Flask. It is designed as a modern destination for gamers to discover games, join events, create accounts, interact with the gaming community, and build their digital player identity.

The platform uses a futuristic dark design inspired by cyberpunk interfaces, competitive gaming dashboards, and modern gaming communities. NEXUS is not only a game showcase—it is planned as a complete gaming ecosystem where players can play, connect, compete, progress, and earn recognition.

The application is deployed on Render and uses a database-backed user system, secure account authentication, Google OAuth, and Cloudflare Turnstile bot protection.

***

## Vision

The vision behind NEXUS is to create a single platform where gamers can:

- Discover interesting and trending games.
- Build a recognizable gaming profile.
- Join gaming events and tournaments.
- Interact with other players through community features.
- Track activity, achievements, rewards, and rankings.
- Compete through leaderboards and tournament brackets.
- Receive a premium, smooth, responsive, and secure gaming experience.

NEXUS aims to grow from a gaming landing page into a complete social and competitive gaming network.

***

## Problem Statement

Gamers often need to use different platforms for different tasks:

- One platform to find games.
- Another platform for tournaments.
- Another platform to communicate with gaming communities.
- Another platform for profiles, content, rankings, or rewards.

This creates a fragmented experience.

**NEXUS solves this problem** by combining game discovery, player profiles, community interactions, events, and competitive features into one unified platform with a strong gaming identity.

***

## Key Objectives

- Build a secure and reliable gaming platform using Flask.
- Provide simple signup, login, logout, and Google OAuth authentication.
- Protect forms and authentication routes from bots using Cloudflare Turnstile.
- Create a responsive, futuristic, and dark gaming interface.
- Allow players to explore games and participate in the NEXUS community.
- Prepare the platform for tournaments, profiles, rewards, leaderboards, and social engagement.
- Keep the system compatible with Render deployment and Python 3.11.
- Never expose passwords, API keys, OAuth secrets, Turnstile keys, or database URLs.

***

## Current Features

### Secure authentication

NEXUS includes a user authentication system with:

- Signup and login functionality.
- Password hashing to avoid storing plain-text passwords.
- Google OAuth login for a faster sign-in experience.
- Secure logout functionality.
- User data stored through SQLAlchemy database models.
- Cloudflare Turnstile verification to reduce spam and automated signup attempts.

### Gaming experience

The current platform includes:

- Game showcase section.
- Interactive game carousel.
- Download section.
- Events section.
- Community section.
- Responsive navigation.
- Login and signup modal forms.
- API routes for games, contact forms, login, signup, and registration.

### Deployment and infrastructure

- Flask backend.
- SQLAlchemy database.
- Render deployment.
- Python 3.11 compatibility.
- Environment-variable-based secret management.
- Health-check route for deployment monitoring.

***

## Technology Stack

| Category | Technology |
|---|---|
| Backend | Python, Flask |
| Database | SQLAlchemy |
| Frontend | HTML, CSS, JavaScript |
| Design Style | Futuristic dark gaming / cyberpunk UI |
| Authentication | Password hashing and Google OAuth |
| Bot Protection | Cloudflare Turnstile |
| Deployment | Render |
| Server Runtime | Python 3.11 |
| APIs | Games, signup, login, contact, registration |
| Version Control | Git and GitHub |

***

## Design Philosophy

NEXUS follows a visual identity built around the idea of a high-tech gaming network.

### Visual direction

- Dark backgrounds for an immersive gaming environment.
- Neon-inspired colors such as cyan, blue, purple, and electric accents.
- Futuristic cards, glowing borders, sharp interface elements, and smooth transitions.
- High-contrast call-to-action buttons.
- Responsive layouts for desktop, tablet, and mobile players.
- Gaming-inspired typography and iconography.
- Clean sections that make games, events, and community content easy to explore.

### User experience goals

The design is built to make the user feel like they are entering a gaming command center rather than a normal website.

Every screen should communicate:

```text
Discover → Connect → Compete → Level Up
```

***

## NEXUS User Journey

```text
Visitor arrives at NEXUS
          ↓
Explores games, events, and community content
          ↓
Creates an account or signs in using Google
          ↓
Completes Turnstile security verification
          ↓
Builds a player profile
          ↓
Saves favorite games and tracks activity
          ↓
Joins community discussions and events
          ↓
Competes in tournaments and leaderboards
          ↓
Earns XP, achievements, rewards, and recognition
```

***

## Platform Architecture

```text
┌──────────────────────────────────────────────┐
│                  NEXUS UI                    │
│ HTML • CSS • JavaScript • Responsive Design  │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│                Flask Backend                 │
│ Routes • Validation • Sessions • APIs        │
└──────────────────────┬───────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
┌───────────────┐ ┌───────────┐ ┌────────────────┐
│ SQLAlchemy DB │ │ Google    │ │ Cloudflare     │
│ Users & Data  │ │ OAuth     │ │ Turnstile      │
└───────────────┘ └───────────┘ └────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │ Render Hosting │
              └────────────────┘
```

***

## Phase 1: Foundation and Security

The first development phase focuses on making the existing project stable, secure, and ready for future features.

### Phase 1 goals

- Fix duplicate signup submissions.
- Ensure `static/js/main.js` loads exactly once.
- Prevent duplicate JavaScript event listeners.
- Improve Turnstile verification and user-facing error messages.
- Keep server-side Turnstile verification enabled using `TURNSTILE_SECRET_KEY`.
- Add CSRF protection without breaking existing JSON API routes.
- Improve the existing User model for profiles.
- Add a secure forgot-password flow.
- Add email verification support.
- Preserve the current Google OAuth, login, signup, logout, game APIs, health route, database, and Render deployment.

### Important Phase 1 rules

```text
Do not reset the database.
Do not delete existing users.
Do not disable Cloudflare Turnstile.
Do not expose environment variables or secret keys.
Do not load main.js more than once.
Do not create duplicate routes or duplicate form event listeners.
Do not replace the whole Flask project.
```

***

## Planned Development Roadmap

### Phase 1 — Foundation

- Fix duplicate signup submissions.
- Fix Turnstile verification and friendly error handling.
- Add CSRF protection safely.
- Improve User profile data.
- Add forgot-password support.
- Add email verification support.

### Phase 2 — Games

- Game search.
- Genre filters.
- Dedicated game detail pages.
- Reviews and ratings.
- Favorite games.
- Personal game library.
- Play tracking.
- Daily login rewards.
- Login streaks.
- XP and level system.
- Achievement badges.

### Phase 3 — Community

- Community posts.
- Comments and replies.
- Likes and follows.
- User activity feed.
- Clans and teams.
- User-submitted games.
- Admin approval workflow.
- Post reporting and moderation.
- Discord, Twitch, and YouTube profile links.

### Phase 4 — Events

- Seasonal gaming events.
- Tournament creation.
- Event registration.
- Tournament brackets.
- Leaderboards and rankings.
- Referral rewards.
- Sponsored tournament support.

### Phase 5 — Monetization

- Premium membership.
- Ad-free platform experience.
- Exclusive gaming content.
- Virtual currency.
- Gaming skins, avatars, and boosts.
- Gaming gear affiliate links.
- Payment integration only after explicit approval and security review.

### Phase 6 — SEO and Admin

- Gaming blog.
- Guides and gaming news.
- SEO-friendly game reviews.
- Public player profiles.
- Schema markup.
- Admin dashboard.
- User management.
- Content moderation.
- Platform analytics.

### Phase 7 — Polish

- Loading states.
- Empty states.
- Clear error messages.
- Improved mobile responsiveness.
- Better accessibility.
- Performance optimization.
- Security hardening.

***

## Security Principles

NEXUS is designed to treat security as a core feature, not an optional addition.

### Security practices

- Passwords must always be hashed.
- Secret keys must remain in Render environment variables.
- Database URLs must never be pushed to GitHub.
- Google OAuth credentials must never be hard-coded.
- Cloudflare Turnstile server-side verification must stay enabled.
- Signup and login attempts should use rate limiting.
- Forms should validate data on both frontend and backend.
- API routes should validate request data before using it.
- Logout should safely clear user sessions.
- Password-reset tokens should be short-lived, one-time use, and stored securely.
- Email verification tokens should expire and must not expose account information.
- Error messages should help users without leaking private security details.

***

## Proposed File Changes for Phase 1

Before modifying the project, the following files should be inspected first. Only files that already exist—or a clearly necessary small addition—should be changed.

| File | Planned purpose |
|---|---|
| `app.py` or main Flask file | Inspect existing routes, Turnstile flow, signup, login, logout, APIs, and configuration |
| `models.py` | Inspect and carefully extend the existing `User` model without deleting current data |
| `templates/index.html` | Remove duplicate `main.js` tags and ensure forms have unique IDs |
| `static/js/main.js` | Add a single guarded signup handler and prevent repeated submissions |
| `requirements.txt` | Confirm installed packages and Python 3.11 compatibility before adding dependencies |
| Existing configuration file | Confirm secrets come from Render environment variables only |
| Existing email/template files | Add password-reset and verification templates only if required |

No project-wide rewrite should happen. No existing route should be duplicated.

***

## Testing Strategy

Every phase should be tested before the next phase begins.

### Signup testing

1. Open the browser developer tools.
2. Select the **Network** tab.
3. Fill in the signup form.
4. Complete Cloudflare Turnstile.
5. Click signup only once.
6. Confirm exactly one request is sent to the signup endpoint.
7. Confirm one account is created.
8. Confirm one success message is displayed.
9. Confirm the button becomes disabled while the request is in progress.
10. Confirm the button becomes active again only if signup fails.

### Turnstile testing

1. Try signup without completing Turnstile.
2. Confirm the user sees a clear security-check message.
3. Complete Turnstile and submit again.
4. Confirm server-side verification succeeds.
5. Confirm no Turnstile secret appears in frontend code, GitHub, browser responses, or logs.

### Render testing

1. Run Python syntax checks locally.
2. Confirm the app starts locally.
3. Commit only the tested changes.
4. Push to GitHub.
5. Let Render deploy automatically.
6. Inspect Render logs for startup errors.
7. Test `/health`.
8. Test login, Google OAuth, signup, logout, `/api/games`, `/api/login`, and `/api/register`.

***

## Command Center Summary

```text
Project Name: NEXUS — Play the Edge
Project Type: Full-Stack Gaming Web Platform
Backend: Flask / Python
Database: SQLAlchemy
Deployment: Render
Security: Password hashing, Google OAuth, Cloudflare Turnstile
UI Style: Futuristic dark gaming interface
Purpose: Game discovery, community, competition, player growth
Status: Active development
Current Focus: Game Radar and My Game Vault (next approved module)
```

***

## Future Identity

NEXUS is being built to become more than a website.

It is intended to become a digital gaming network where every player can have a profile, every game can have a community, every event can become a competition, and every achievement can become part of a player’s legacy.

```text
NEXUS is where players discover the next game,
build their identity,
find their squad,
and play at the edge.
```

# Play the Edge. Own the Arena.
