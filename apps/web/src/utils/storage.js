const THEME_KEY = "corpner.theme.v2";
const SHARED_THEME_KEY = "theme";

export const SIDEBAR_COLLAPSED_KEY = "corpner.sidebar_collapsed";
export const GLOBAL_CANCEL_KEY = "corpner.show_cancelled";

export function storageBool(key, fallback = false) {
  try {
    const value = localStorage.getItem(key);
    return value === null ? fallback : value === "1" || value === "true";
  } catch {
    return fallback;
  }
}

export function setStorageBool(key, value) {
  try {
    localStorage.setItem(key, value ? "1" : "0");
  } catch {
    // ignore unavailable storage
  }
}

export function loadTheme() {
  try {
    return localStorage.getItem(SHARED_THEME_KEY) || localStorage.getItem(THEME_KEY) || "light";
  } catch {
    return "light";
  }
}

export function saveTheme(theme) {
  try {
    localStorage.setItem(SHARED_THEME_KEY, theme);
    localStorage.setItem(THEME_KEY, theme);
  } catch {
    // ignore unavailable storage
  }
}

