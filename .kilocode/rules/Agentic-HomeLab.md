# Agentic-HomeLab.md

Our Agentic-HomeLab project, consists of two sub-directories housing our backend and front-end (Agentic-Backend and Agentic-Frontend). These two sub-directories, implement their code/infrastructure via docker containers (there is a docker-compose.yml in each of these direcotires). We run, test and manage these applications by using docker compose commands (not docker-compose). We have a high-level API documentation that we have been using keep running API documentation, we want to keep this up to date, organized and contexutally aware, this is called API_DOCUMENTATION.md

## Guidelines

- Follow modern agentic architecture and design principals
- Backend workflows should be scoped to the logged in user/user-session. 
- Backend workflows should have their own logs in the existing pub/sub design, that are ultimately exposed to our front-end via websocket for live updates

