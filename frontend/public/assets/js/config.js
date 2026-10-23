const standalonePorts = new Set(["8000", "5500", "8080"]);

export const API_BASE_URL = standalonePorts.has(window.location.port)
  ? "http://localhost:5000/api"
  : `${window.location.origin}/api`;
