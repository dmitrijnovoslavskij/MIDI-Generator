const { app, BrowserWindow, ipcMain } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

// Все файлы лежат рядом с electron_main.js (в корне репо / install dir)
const BASE_DIR = path.dirname(__filename);

let mainWindow = null;
let backendProcess = null;

const IS_WINDOWS = process.platform === "win32";

// ─── Найти Python в venv ───────────────────────────────────────────────────
function findPython() {
  const candidates = [
    path.join(BASE_DIR, "runtime", "venv", "bin", "python3"),        // macOS
    path.join(BASE_DIR, "runtime", "venv", "bin", "python"),         // macOS alt
    path.join(BASE_DIR, "runtime", "venv", "Scripts", "python.exe"), // Windows
  ];
  for (const p of candidates) {
    if (fs.existsSync(p)) return p;
  }
  return null;
}

// ─── Запустить FastAPI backend ─────────────────────────────────────────────
function startBackend() {
  const pythonPath = findPython();

  if (!pythonPath) {
    console.error("[ERROR] Python not found in runtime/venv");
    return;
  }

  console.log("[PYTHON] Using:", pythonPath);

  backendProcess = spawn(
    pythonPath,
    ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
    {
      // cwd = корень репо, где лежит main.py напрямую
      cwd: BASE_DIR,
      env: { ...process.env },
      stdio: "ignore",
      ...(IS_WINDOWS && {
        windowsHide: true,
        detached: false,
      }),
    }
  );

  backendProcess.on("error", (err) => console.error("[BACKEND ERROR]", err));
  backendProcess.on("exit",  (code) => console.log("[BACKEND] exit:", code));
}

// ─── Создать окно ──────────────────────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1000,
    height: 750,
    title: "MIDI Gen",
    icon: path.join(BASE_DIR, "icon.png"),
    autoHideMenuBar: IS_WINDOWS,
    webPreferences: {
      preload: path.join(BASE_DIR, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      devTools: !app.isPackaged,
    },
  });

  if (IS_WINDOWS) {
    mainWindow.setMenuBarVisibility(false);
  }

  // Ждём backend, затем открываем
  const tryLoad = (attempts) => {
    mainWindow.loadURL("http://127.0.0.1:8000").catch(() => {
      if (attempts > 0) setTimeout(() => tryLoad(attempts - 1), 1000);
      else console.error("[ERROR] Backend не ответил за 15 секунд");
    });
  };
  setTimeout(() => tryLoad(15), 1000);

  mainWindow.on("closed", () => { mainWindow = null; });
}

// ─── Drag-and-drop MIDI ────────────────────────────────────────────────────
ipcMain.on("start-native-drag", (event, filePath) => {
  if (typeof filePath !== "string") return;
  const abs = path.resolve(filePath);
  if (!fs.existsSync(abs)) return;
  event.sender.startDrag({
    file: abs,
    icon: path.join(BASE_DIR, "icon.png"),
  });
});

// ─── Lifecycle ────────────────────────────────────────────────────────────
app.whenReady().then(() => {
  startBackend();
  createWindow();
});

app.on("window-all-closed", () => {
  if (backendProcess) backendProcess.kill("SIGTERM");
  app.quit();
});

app.on("activate", () => {
  if (mainWindow === null) createWindow();
});