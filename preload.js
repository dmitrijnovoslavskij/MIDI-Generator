// preload.js
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  startDrag: (filePath) => {
    if (typeof filePath !== 'string') return;

    ipcRenderer.send('start-native-drag', filePath);
  }
});