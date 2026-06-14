import { useEffect, useState } from "react";

import { GLOBAL_CANCEL_KEY, loadTheme, saveTheme, SIDEBAR_COLLAPSED_KEY, setStorageBool, storageBool } from "../utils/storage.js";

export function useAppPreferences() {
  const [theme, setTheme] = useState(loadTheme);
  const [collapsed, setCollapsed] = useState(() => storageBool(SIDEBAR_COLLAPSED_KEY));
  const [showCancelled, setShowCancelled] = useState(() => storageBool(GLOBAL_CANCEL_KEY));

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    document.documentElement.style.colorScheme = theme;
    saveTheme(theme);
  }, [theme]);

  useEffect(() => {
    document.body.classList.toggle("sidebar-collapsed", collapsed);
    setStorageBool(SIDEBAR_COLLAPSED_KEY, collapsed);
  }, [collapsed]);

  useEffect(() => {
    setStorageBool(GLOBAL_CANCEL_KEY, showCancelled);
  }, [showCancelled]);

  return {
    theme,
    setTheme,
    collapsed,
    setCollapsed,
    showCancelled,
    setShowCancelled
  };
}
