"""Interactive single-page Web UI with File Upload, Voice Recording, and Audio File Deletion."""

def get_frontend_html() -> str:
    """Return the interactive HTML/JS frontend page."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Whisper Transcription Studio</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    @keyframes pulse-subtle { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }
    .animate-pulse-subtle { animation: pulse-subtle 1.8s infinite ease-in-out; }
    @keyframes pulse-rec { 0%, 100% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.08); opacity: 0.85; } }
    .animate-rec { animation: pulse-rec 1.2s infinite ease-in-out; }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen font-sans flex flex-col items-center py-10 px-4">
  
  <!-- Header -->
  <header class="max-w-3xl w-full text-center mb-8">
    <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold mb-3">
      ⚡ Faster-Whisper CPU Powered
    </div>
    <h1 class="text-3xl md:text-4xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-indigo-300 bg-clip-text text-transparent">
      Audio & Voice Transcription Studio
    </h1>
    <p class="text-slate-400 mt-2 text-sm md:text-base">
      Upload audio files or record live voice. Includes automatic WAV conversion and full audio removal controls.
    </p>
  </header>

  <!-- Main Container -->
  <main class="max-w-3xl w-full space-y-6">
    
    <!-- Input Card -->
    <div class="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-sm space-y-5">
      
      <!-- Mode Tabs (Upload vs Record) -->
      <div class="flex items-center p-1 bg-slate-950/80 rounded-xl border border-slate-800">
        <button id="tabUpload" type="button" class="flex-1 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white transition flex items-center justify-center gap-2 shadow">
          📁 Upload Audio File
        </button>
        <button id="tabRecord" type="button" class="flex-1 py-2 text-xs font-semibold rounded-lg text-slate-400 hover:text-slate-200 transition flex items-center justify-center gap-2">
          🎙️ Live Voice Recording
        </button>
      </div>

      <!-- Mode 1: File Upload Section -->
      <div id="sectionUpload" class="space-y-4">
        <!-- Upload Drop Zone (Click or Drag) -->
        <div id="dropZone" class="border-2 border-dashed border-slate-700 hover:border-indigo-500 rounded-xl p-8 text-center cursor-pointer transition-all bg-slate-950/40 relative">
          <input type="file" id="audioFile" accept=".wav,.mp3,.m4a,.flac,.ogg,.webm,.aac,.opus,audio/*" style="display: none;">
          <svg class="mx-auto h-12 w-12 text-slate-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 100-6 3 3 0 000 6z" />
          </svg>
          <p class="text-sm font-semibold text-slate-200" id="dropText">Click to select audio or drag & drop</p>
          <p class="text-xs text-slate-500 mt-1">WAV, MP3, M4A, OGG, FLAC, WebM · Up to 500 MB</p>
        </div>

        <!-- Prominent Selected Audio Card (Shown immediately upon selection) -->
        <div id="selectedAudioCard" class="hidden p-4 rounded-xl bg-slate-900/90 border border-indigo-500/50 shadow-xl space-y-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3 truncate mr-2">
              <div class="h-10 w-10 rounded-lg bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center font-bold text-lg shrink-0">
                🎵
              </div>
              <div class="truncate">
                <p id="selectedNameDisplay" class="text-sm font-bold text-slate-100 truncate">audio.mp3</p>
                <p id="selectedSizeDisplay" class="text-xs text-indigo-400 font-mono mt-0.5">0.0 MB</p>
              </div>
            </div>
            <button id="btnRemoveSelectedAudio" type="button" class="px-3 py-1.5 rounded-lg bg-red-950/40 hover:bg-red-900/60 text-red-300 text-xs font-semibold border border-red-800/60 transition flex items-center gap-1 shrink-0">
              ✕ Remove
            </button>
          </div>
          <audio id="audioPreview" controls class="w-full rounded-lg bg-slate-950"></audio>
        </div>
      </div>

      <!-- Mode 2: Voice Recording Section -->
      <div id="sectionRecord" class="hidden space-y-5 py-4 text-center">
        <div class="flex flex-col items-center justify-center space-y-3">
          <button id="btnRecordToggle" type="button" class="h-20 w-20 rounded-full bg-red-600 hover:bg-red-500 text-white flex items-center justify-center shadow-lg shadow-red-600/30 transition transform hover:scale-105 active:scale-95">
            <svg id="micIcon" class="h-8 w-8" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
              <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
            </svg>
            <div id="stopSquare" class="h-6 w-6 bg-white rounded-sm hidden"></div>
          </button>
          <div>
            <p id="recordStatusLabel" class="text-sm font-semibold text-slate-200">Click to start recording</p>
            <p id="recordTimer" class="text-xs font-mono text-red-400 mt-0.5 hidden">00:00</p>
          </div>
        </div>
        <div id="recordPreviewContainer" class="hidden pt-2 border-t border-slate-800">
          <p class="text-xs text-slate-400 mb-2">Recorded audio preview (16kHz WAV):</p>
          <audio id="recordAudioPreview" controls class="w-full"></audio>
        </div>
      </div>

      <!-- Options Row (Language, Hardware & Auto-Delete) -->
      <div class="space-y-3 pt-2 border-t border-slate-800/80">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          <!-- Language Selector -->
          <div class="flex items-center gap-2">
            <label for="languageSelect" class="font-medium text-slate-400 shrink-0">Language:</label>
            <select id="languageSelect" class="w-full bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-indigo-500">
              <option value="">Auto Detect (Whisper AI)</option>
              <option value="en">English (Fastest)</option>
              <option value="es">Spanish</option>
              <option value="fr">French</option>
              <option value="de">German</option>
              <option value="zh">Chinese</option>
              <option value="ja">Japanese</option>
              <option value="hi">Hindi</option>
              <option value="ta">Tamil</option>
            </select>
          </div>

          <!-- Hardware Accelerator Selector -->
          <div class="flex items-center gap-2">
            <label for="deviceSelect" class="font-medium text-slate-400 shrink-0">Hardware:</label>
            <select id="deviceSelect" class="w-full bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-indigo-500">
              <option value="cpu" selected>💻 CPU (Default · int8)</option>
              <option value="gpu" id="optGpu" disabled class="text-slate-500">⚡ GPU / CUDA (No GPU detected)</option>
            </select>
          </div>
        </div>

        <div class="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
          <label class="flex items-center gap-2 cursor-pointer hover:text-slate-300">
            <input type="checkbox" id="chkAutoDelete" checked class="rounded bg-slate-800 border-slate-700 text-indigo-600 focus:ring-0">
            <span>Auto-delete audio from server after transcription</span>
          </label>
          <span id="gpuStatusBadge" class="text-[11px] text-slate-500 font-mono"></span>
        </div>
      </div>

      <!-- Submit Button -->
      <button id="submitBtn" disabled class="w-full py-3 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-600 font-semibold text-sm transition-all flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/20">
        <span>Start Transcription</span>
      </button>

    </div>

    <!-- Status Card (Hidden by default) -->
    <div id="statusCard" class="hidden bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div id="statusSpinner" class="h-3 w-3 rounded-full bg-amber-400 animate-pulse-subtle"></div>
          <span class="text-sm font-semibold capitalize" id="statusText">Queued</span>
        </div>
        <span class="text-xs font-mono text-slate-500" id="jobIdLabel"></span>
      </div>
      <p class="text-xs text-slate-400 mt-2" id="statusMessage">Uploading and processing audio...</p>

      <!-- Real-Time Live Progress Bar for Long Audio -->
      <div id="progressContainer" class="mt-4 pt-3 border-t border-slate-800/80">
        <div class="flex justify-between text-xs text-slate-400 mb-1.5">
          <span id="progressPercentLabel" class="font-semibold text-indigo-400 font-mono">0%</span>
          <span id="progressTimeLabel" class="text-slate-500 text-[11px] font-mono">Connecting live stream...</span>
        </div>
        <div class="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800/80">
          <div id="progressBarFill" class="bg-gradient-to-r from-indigo-500 via-purple-500 to-indigo-400 h-2 rounded-full transition-all duration-300" style="width: 0%"></div>
        </div>
      </div>
    </div>

    <!-- Results Card (Hidden by default) -->
    <div id="resultsCard" class="hidden bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
      
      <!-- Metadata Header & Actions -->
      <div class="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 class="text-lg font-bold text-slate-100">Transcription Result</h2>
          <div class="flex items-center gap-3 text-xs text-slate-400 mt-1">
            <span>Hardware: <strong class="text-amber-400 uppercase font-mono" id="resDevice">CPU</strong></span>
            <span>•</span>
            <span>Language: <strong class="text-indigo-400 uppercase" id="resLanguage">EN</strong></span>
            <span>•</span>
            <span>Duration: <strong class="text-slate-200" id="resDuration">0s</strong></span>
          </div>
        </div>

        <!-- Action Buttons (Downloads + Delete) -->
        <div class="flex flex-wrap items-center gap-2">
          <a id="downloadSrt" href="#" download class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700 flex items-center gap-1 transition">
            📥 SRT
          </a>
          <a id="downloadVtt" href="#" download class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700 flex items-center gap-1 transition">
            📥 VTT
          </a>
          <a id="downloadJson" href="#" download class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700 flex items-center gap-1 transition">
            📥 JSON
          </a>
          <button id="btnDeleteServerFile" type="button" class="px-3 py-1.5 rounded-lg bg-red-950/40 hover:bg-red-900/60 text-xs font-medium text-red-300 border border-red-800/60 flex items-center gap-1 transition">
            🗑️ Delete from Server
          </button>
        </div>
      </div>

      <!-- Full Transcript -->
      <div>
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-semibold uppercase tracking-wider text-slate-400">Full Text</span>
          <button id="copyBtn" class="text-xs text-indigo-400 hover:text-indigo-300 font-medium transition">
            Copy text
          </button>
        </div>
        <div id="fullTranscriptText" class="bg-slate-950 border border-slate-800/80 rounded-xl p-4 text-sm text-slate-300 leading-relaxed max-h-60 overflow-y-auto whitespace-pre-wrap"></div>
      </div>

      <!-- Timestamped Segments Breakdown -->
      <div>
        <span class="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-2">Segment Timestamps</span>
        <div id="segmentsList" class="space-y-2 max-h-72 overflow-y-auto pr-1"></div>
      </div>

    </div>

    <!-- Recent Transcriptions Section (Session Recovery) -->
    <div id="recentJobsCard" class="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl">
      <div class="flex items-center justify-between mb-3 border-b border-slate-800 pb-3">
        <div>
          <h3 class="text-sm font-bold text-slate-200">Recent Transcriptions</h3>
          <p class="text-[11px] text-slate-500">Pick any past or long-running transcription without losing your place</p>
        </div>
        <button id="btnRefreshJobs" type="button" class="text-xs text-indigo-400 hover:text-indigo-300 transition">
          🔄 Refresh
        </button>
      </div>
      <div id="recentJobsList" class="space-y-2 max-h-48 overflow-y-auto pr-1 text-xs">
        <span class="text-slate-500">Loading history...</span>
      </div>
    </div>

  </main>

  <script>
    // Tab Elements
    const tabUpload = document.getElementById('tabUpload');
    const tabRecord = document.getElementById('tabRecord');
    const sectionUpload = document.getElementById('sectionUpload');
    const sectionRecord = document.getElementById('sectionRecord');

    // File Upload Elements
    const dropZone = document.getElementById('dropZone');
    const audioFileInput = document.getElementById('audioFile');
    const dropText = document.getElementById('dropText');
    const audioPreview = document.getElementById('audioPreview');
    const selectedAudioCard = document.getElementById('selectedAudioCard');
    const selectedNameDisplay = document.getElementById('selectedNameDisplay');
    const selectedSizeDisplay = document.getElementById('selectedSizeDisplay');
    const btnRemoveSelectedAudio = document.getElementById('btnRemoveSelectedAudio');

    // Recording Elements
    const btnRecordToggle = document.getElementById('btnRecordToggle');
    const micIcon = document.getElementById('micIcon');
    const stopSquare = document.getElementById('stopSquare');
    const recordStatusLabel = document.getElementById('recordStatusLabel');
    const recordTimer = document.getElementById('recordTimer');
    const recordPreviewContainer = document.getElementById('recordPreviewContainer');
    const recordAudioPreview = document.getElementById('recordAudioPreview');

    // Global Action Elements
    const submitBtn = document.getElementById('submitBtn');
    const languageSelect = document.getElementById('languageSelect');
    const deviceSelect = document.getElementById('deviceSelect');
    const gpuStatusBadge = document.getElementById('gpuStatusBadge');
    const chkAutoDelete = document.getElementById('chkAutoDelete');

    // Status & Result Elements
    const statusCard = document.getElementById('statusCard');
    const statusSpinner = document.getElementById('statusSpinner');
    const statusText = document.getElementById('statusText');
    const statusMessage = document.getElementById('statusMessage');
    const jobIdLabel = document.getElementById('jobIdLabel');

    const resultsCard = document.getElementById('resultsCard');
    const resDevice = document.getElementById('resDevice');
    const resLanguage = document.getElementById('resLanguage');
    const resDuration = document.getElementById('resDuration');
    const fullTranscriptText = document.getElementById('fullTranscriptText');
    const segmentsList = document.getElementById('segmentsList');
    const copyBtn = document.getElementById('copyBtn');

    const downloadSrt = document.getElementById('downloadSrt');
    const downloadVtt = document.getElementById('downloadVtt');
    const downloadJson = document.getElementById('downloadJson');
    const btnDeleteServerFile = document.getElementById('btnDeleteServerFile');

    // Progress Bar & History Elements
    const progressPercentLabel = document.getElementById('progressPercentLabel');
    const progressTimeLabel = document.getElementById('progressTimeLabel');
    const progressBarFill = document.getElementById('progressBarFill');
    const recentJobsList = document.getElementById('recentJobsList');
    const btnRefreshJobs = document.getElementById('btnRefreshJobs');

    let currentFile = null;
    let currentJobId = null;
    let activeEventSource = null;
    let pollTimeout = null;
    let pollDelay = 2500;
    let mediaRecorder = null;
    let audioChunks = [];
    let isRecording = false;
    let recordingStartTime = null;
    let timerInterval = null;

    // --- Tab Switching ---
    tabUpload.addEventListener('click', () => {
      tabUpload.className = "flex-1 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white transition flex items-center justify-center gap-2 shadow";
      tabRecord.className = "flex-1 py-2 text-xs font-semibold rounded-lg text-slate-400 hover:text-slate-200 transition flex items-center justify-center gap-2";
      sectionUpload.classList.remove('hidden');
      sectionRecord.classList.add('hidden');
    });

    tabRecord.addEventListener('click', () => {
      tabRecord.className = "flex-1 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white transition flex items-center justify-center gap-2 shadow";
      tabUpload.className = "flex-1 py-2 text-xs font-semibold rounded-lg text-slate-400 hover:text-slate-200 transition flex items-center justify-center gap-2";
      sectionRecord.classList.remove('hidden');
      sectionUpload.classList.add('hidden');
    });

    // --- File Selection & Drag-and-Drop ---
    dropZone.addEventListener('click', () => {
      audioFileInput.value = '';
      audioFileInput.click();
    });

    ['dragenter', 'dragover'].forEach(name => {
      dropZone.addEventListener(name, (e) => {
        e.preventDefault();
        dropZone.classList.add('border-indigo-500', 'bg-indigo-500/10');
      });
    });

    ['dragleave', 'drop'].forEach(name => {
      dropZone.addEventListener(name, (e) => {
        e.preventDefault();
        dropZone.classList.remove('border-indigo-500', 'bg-indigo-500/10');
      });
    });

    dropZone.addEventListener('drop', (e) => {
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        handleFileSelected(e.dataTransfer.files[0]);
      }
    });

    audioFileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) {
        handleFileSelected(e.target.files[0]);
      }
    });

    function handleFileSelected(file) {
      if (!file) return;

      const MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024;
      if (file.size > MAX_FILE_SIZE_BYTES) {
        alert(`File exceeds size limit (${(file.size / (1024 * 1024)).toFixed(1)} MB). Maximum allowed upload size is 500 MB.`);
        resetAudioSelection();
        return;
      }

      currentFile = file;

      // Update Prominent Selected Audio Card
      selectedNameDisplay.innerText = file.name;
      const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
      const sizeKb = (file.size / 1024).toFixed(1);
      selectedSizeDisplay.innerText = sizeMb >= 1 ? `${sizeMb} MB` : `${sizeKb} KB`;

      audioPreview.src = URL.createObjectURL(file);
      selectedAudioCard.classList.remove('hidden');

      dropText.innerHTML = `Selected: <strong class="text-indigo-400">${file.name}</strong>`;
      submitBtn.disabled = false;
    }

    // Clear / Remove Selected Audio
    btnRemoveSelectedAudio.addEventListener('click', () => {
      resetAudioSelection();
    });

    function resetAudioSelection() {
      currentFile = null;
      audioFileInput.value = '';
      audioPreview.src = '';
      selectedAudioCard.classList.add('hidden');
      dropText.innerText = "Click to select audio or drag & drop";

      recordAudioPreview.src = '';
      recordPreviewContainer.classList.add('hidden');
      recordStatusLabel.innerText = "Click to start recording";

      submitBtn.disabled = true;
    }

    // --- Voice Recording & In-Browser WAV Conversion ---
    btnRecordToggle.addEventListener('click', async () => {
      if (!isRecording) {
        startRecording();
      } else {
        stopRecording();
      }
    });

    async function startRecording() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioChunks = [];
        mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = (e) => {
          if (e.data.size > 0) audioChunks.push(e.data);
        };

        mediaRecorder.onstop = async () => {
          stream.getTracks().forEach(t => t.stop());
          const rawBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType || 'audio/webm' });
          recordStatusLabel.innerText = "Converting audio to 16kHz WAV...";
          
          try {
            const wavBlob = await convertBlobToWav(rawBlob);
            const wavFile = new File([wavBlob], `voice_${Date.now()}.wav`, { type: 'audio/wav' });
            currentFile = wavFile;

            recordAudioPreview.src = URL.createObjectURL(wavBlob);
            recordPreviewContainer.classList.remove('hidden');
            recordStatusLabel.innerHTML = `Recording ready: <strong class="text-emerald-400">${(wavBlob.size / 1024).toFixed(1)} KB WAV</strong>`;
            submitBtn.disabled = false;
          } catch (err) {
            recordStatusLabel.innerText = "Audio conversion failed: " + err.message;
          }
        };

        mediaRecorder.start();
        isRecording = true;

        btnRecordToggle.className = "h-20 w-20 rounded-full bg-red-600 text-white flex items-center justify-center shadow-lg shadow-red-600/40 animate-rec";
        micIcon.classList.add('hidden');
        stopSquare.classList.remove('hidden');
        recordStatusLabel.innerText = "Recording voice... Click to Stop";
        recordTimer.classList.remove('hidden');

        recordingStartTime = Date.now();
        timerInterval = setInterval(() => {
          const elapsedSec = Math.floor((Date.now() - recordingStartTime) / 1000);
          const m = Math.floor(elapsedSec / 60).toString().padStart(2, '0');
          const s = (elapsedSec % 60).toString().padStart(2, '0');
          recordTimer.innerText = `${m}:${s}`;
        }, 500);

      } catch (err) {
        alert("Microphone access denied or not supported: " + err.message);
      }
    }

    function stopRecording() {
      if (!mediaRecorder) return;
      mediaRecorder.stop();
      isRecording = false;
      clearInterval(timerInterval);

      btnRecordToggle.className = "h-20 w-20 rounded-full bg-red-600 hover:bg-red-500 text-white flex items-center justify-center shadow-lg shadow-red-600/30 transition transform hover:scale-105";
      micIcon.classList.remove('hidden');
      stopSquare.classList.add('hidden');
      recordTimer.classList.add('hidden');
    }

    // Convert raw browser audio into standard 16kHz 16-bit PCM WAV Blob
    async function convertBlobToWav(blob) {
      const arrayBuffer = await blob.arrayBuffer();
      const targetSampleRate = 16000;
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: targetSampleRate });
      const decodedBuffer = await audioCtx.decodeAudioData(arrayBuffer);

      const length = decodedBuffer.length;
      const monoData = new Float32Array(length);
      for (let i = 0; i < length; i++) {
        let sum = 0;
        for (let c = 0; c < decodedBuffer.numberOfChannels; c++) {
          sum += decodedBuffer.getChannelData(c)[i];
        }
        monoData[i] = sum / decodedBuffer.numberOfChannels;
      }

      const dataLength = length * 2;
      const buffer = new ArrayBuffer(44 + dataLength);
      const view = new DataView(buffer);

      function writeStr(offset, str) {
        for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
      }

      writeStr(0, 'RIFF');
      view.setUint32(4, 36 + dataLength, true);
      writeStr(8, 'WAVE');
      writeStr(12, 'fmt ');
      view.setUint32(16, 16, true);
      view.setUint16(20, 1, true); // PCM format
      view.setUint16(22, 1, true); // Mono
      view.setUint32(24, decodedBuffer.sampleRate, true);
      view.setUint32(28, decodedBuffer.sampleRate * 2, true);
      view.setUint16(32, 2, true);
      view.setUint16(34, 16, true);
      writeStr(36, 'data');
      view.setUint32(40, dataLength, true);

      let offset = 44;
      for (let i = 0; i < length; i++) {
        let s = Math.max(-1, Math.min(1, monoData[i]));
        s = s < 0 ? s * 0x8000 : s * 0x7FFF;
        view.setInt16(offset, s, true);
        offset += 2;
      }

      audioCtx.close();
      return new Blob([view], { type: 'audio/wav' });
    }

    // --- Submit to Transcribe API ---
    submitBtn.addEventListener('click', async () => {
      if (!currentFile) return;

      currentJobAutoDelete = chkAutoDelete.checked;
      submitBtn.disabled = true;
      submitBtn.innerHTML = `<span>Uploading to Whisper API...</span>`;

      statusCard.classList.remove('hidden');
      resultsCard.classList.add('hidden');
      statusText.innerText = "Queued";
      statusSpinner.className = "h-3 w-3 rounded-full bg-amber-400 animate-pulse-subtle";
      statusMessage.innerText = "Audio uploaded. Queued for background processing...";

      const formData = new FormData();
      formData.append('file', currentFile);
      if (languageSelect.value) {
        formData.append('language', languageSelect.value);
      }
      formData.append('device', deviceSelect.value);
      formData.append('auto_delete', chkAutoDelete.checked ? 'true' : 'false');

      try {
        const resp = await fetch('/api/v1/transcriptions', {
          method: 'POST',
          body: formData,
        });

        if (!resp.ok) {
          const err = await resp.json();
          throw new Error(err.detail || 'Upload failed');
        }

        const data = await resp.json();
        currentJobId = data.job_id;
        startJobTracking(data.job_id);

      } catch (err) {
        statusText.innerText = "Error";
        statusSpinner.className = "h-3 w-3 rounded-full bg-red-500";
        statusMessage.innerText = err.message;
        submitBtn.disabled = false;
        submitBtn.innerHTML = `<span>Start Transcription</span>`;
      }
    });

    // --- Real-time SSE Push Tracking with Adaptive Fallback ---
    function startJobTracking(jobId) {
      currentJobId = jobId;
      localStorage.setItem('whisper_active_job', jobId);
      jobIdLabel.innerText = "ID: " + jobId.substring(0, 8);

      statusCard.classList.remove('hidden');
      progressBarFill.style.width = '0%';
      progressPercentLabel.innerText = '0%';
      progressTimeLabel.innerText = 'Connecting live stream...';

      if (pollTimeout) {
        clearTimeout(pollTimeout);
        pollTimeout = null;
      }
      if (activeEventSource) {
        activeEventSource.close();
        activeEventSource = null;
      }

      // Use Server-Sent Events (SSE) for 0 repetitive polling calls
      if (window.EventSource) {
        activeEventSource = new EventSource(`/api/v1/transcriptions/${jobId}/events`);

        activeEventSource.onmessage = (evt) => {
          try {
            const job = JSON.parse(evt.data);
            updateJobState(job);
          } catch (e) {
            console.error("SSE parse error", e);
          }
        };

        activeEventSource.onerror = (err) => {
          // If SSE connection closes or drops, fall back gracefully
          if (activeEventSource) {
            activeEventSource.close();
            activeEventSource = null;
          }
          startPollingFallback(jobId);
        };
      } else {
        startPollingFallback(jobId);
      }
    }

    function updateJobState(job) {
      statusText.innerText = job.status;
      const pct = Math.min(100, Math.max(0, job.progress || 0));
      progressBarFill.style.width = pct + '%';
      progressPercentLabel.innerText = pct + '%';

      const hw = ((job.device || deviceSelect.value || 'cpu') === 'cuda' ? 'GPU' : 'CPU');

      if (job.status === 'processing') {
        statusSpinner.className = "h-3 w-3 rounded-full bg-blue-500 animate-pulse-subtle";
        if (job.duration && job.duration > 0) {
          const processed = Math.min(job.duration, (pct / 100) * job.duration);
          progressTimeLabel.innerText = `${formatSec(processed)} / ${formatSec(job.duration)}`;
          statusMessage.innerText = `Faster-Whisper transcribing on ${hw} (${pct}%)...`;
        } else {
          progressTimeLabel.innerText = 'Live inference';
          statusMessage.innerText = `Faster-Whisper transcribing on ${hw} (${pct}%)...`;
        }
      } else if (job.status === 'queued') {
        statusSpinner.className = "h-3 w-3 rounded-full bg-amber-400 animate-pulse-subtle";
        progressTimeLabel.innerText = 'Waiting for worker';
        statusMessage.innerText = `Queued for ${hw} inference worker...`;
      } else if (job.status === 'completed') {
        progressBarFill.style.width = '100%';
        progressPercentLabel.innerText = '100%';
        progressTimeLabel.innerText = 'Complete';
        statusSpinner.className = "h-3 w-3 rounded-full bg-emerald-500";
        statusMessage.innerText = "Transcription completed successfully!";
        submitBtn.disabled = false;
        submitBtn.innerHTML = `<span>Transcribe Another</span>`;

        if (activeEventSource) {
          activeEventSource.close();
          activeEventSource = null;
        }
        if (pollTimeout) {
          clearTimeout(pollTimeout);
          pollTimeout = null;
        }

        loadResults(job.job_id || currentJobId);
        refreshRecentJobs();
      } else if (job.status === 'failed') {
        statusSpinner.className = "h-3 w-3 rounded-full bg-red-500";
        statusMessage.innerText = "Failed: " + (job.error || "Unknown error");
        submitBtn.disabled = false;
        submitBtn.innerHTML = `<span>Try Again</span>`;

        if (activeEventSource) {
          activeEventSource.close();
          activeEventSource = null;
        }
        if (pollTimeout) {
          clearTimeout(pollTimeout);
          pollTimeout = null;
        }
        refreshRecentJobs();
      }
    }

    // --- Fallback Polling (Only used if SSE connection fails) ---
    function startPollingFallback(jobId) {
      if (pollTimeout) clearTimeout(pollTimeout);
      pollDelay = 3000;

      async function checkStatus() {
        try {
          const resp = await fetch(`/api/v1/transcriptions/${jobId}`);
          if (!resp.ok) {
            pollTimeout = setTimeout(checkStatus, pollDelay);
            return;
          }
          const job = await resp.json();
          updateJobState(job);

          if (job.status === 'processing' || job.status === 'queued') {
            pollDelay = Math.min(pollDelay + 1000, 6000);
            pollTimeout = setTimeout(checkStatus, pollDelay);
          }
        } catch (e) {
          console.error("Polling error", e);
          pollDelay = Math.min(pollDelay + 2000, 8000);
          pollTimeout = setTimeout(checkStatus, pollDelay);
        }
      }

      pollTimeout = setTimeout(checkStatus, pollDelay);
    }

    // --- Render Results ---
    async function loadResults(jobId) {
      try {
        const resp = await fetch(`/api/v1/transcriptions/${jobId}/result`);
        if (!resp.ok) return;

        const data = await resp.json();

        resDevice.innerText = (data.device || "cpu").toUpperCase();
        resLanguage.innerText = data.language || "EN";
        resDuration.innerText = (data.duration || 0).toFixed(1) + "s";
        fullTranscriptText.innerText = data.text || "(No spoken speech detected)";

        downloadSrt.href = `/api/v1/transcriptions/${jobId}/download?format=srt`;
        downloadVtt.href = `/api/v1/transcriptions/${jobId}/download?format=vtt`;
        downloadJson.href = `/api/v1/transcriptions/${jobId}/download?format=json`;

        segmentsList.innerHTML = '';
        (data.segments || []).forEach(seg => {
          const item = document.createElement('div');
          item.className = "flex items-start gap-3 p-2.5 rounded-lg bg-slate-950/70 border border-slate-800/60 text-xs";
          item.innerHTML = `
            <span class="font-mono text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded shrink-0">
              ${formatSec(seg.start)} - ${formatSec(seg.end)}
            </span>
            <span class="text-slate-300 leading-relaxed">${escapeHtml(seg.text)}</span>
          `;
          segmentsList.appendChild(item);
        });

        resultsCard.classList.remove('hidden');
        btnDeleteServerFile.classList.remove('hidden');
      } catch (e) {
        console.error("Failed to load result", e);
      }
    }

    // --- Delete Audio & Job from Server ---
    btnDeleteServerFile.addEventListener('click', async () => {
      if (!currentJobId) return;
      if (confirm("Permanently delete this audio file and its job record from the server?")) {
        await deleteServerFile(currentJobId, true);
      }
    });

    async function deleteServerFile(jobId, alertUser = true) {
      try {
        const resp = await fetch(`/api/v1/transcriptions/${jobId}`, { method: 'DELETE' });
        if (resp.ok) {
          if (alertUser) {
            alert("Audio file and job record have been deleted from disk and database.");
            resultsCard.classList.add('hidden');
            statusCard.classList.add('hidden');
            resetAudioSelection();
            refreshRecentJobs();
          }
        }
      } catch (e) {
        console.error("Failed to delete server file:", e);
      }
    }

    function formatSec(sec) {
      const m = Math.floor(sec / 60).toString().padStart(2, '0');
      const s = Math.floor(sec % 60).toString().padStart(2, '0');
      return `${m}:${s}`;
    }

    function escapeHtml(text) {
      const div = document.createElement('div');
      div.innerText = text;
      return div.innerHTML;
    }

    copyBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(fullTranscriptText.innerText).then(() => {
        copyBtn.innerText = "Copied!";
        setTimeout(() => copyBtn.innerText = "Copy text", 2000);
      });
    });

    // --- Recent Transcriptions List & Session Recovery ---
    async function refreshRecentJobs() {
      try {
        const resp = await fetch('/api/v1/transcriptions?limit=6');
        if (!resp.ok) return;
        const jobs = await resp.json();

        if (!jobs || jobs.length === 0) {
          recentJobsList.innerHTML = `<span class="text-slate-500 italic">No recent transcriptions found.</span>`;
          return;
        }

        recentJobsList.innerHTML = '';
        jobs.forEach(job => {
          const div = document.createElement('div');
          div.className = "flex items-center justify-between p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700/80 transition";

          let statusBadge = '';
          if (job.status === 'completed') {
            statusBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Done (${(job.duration || 0).toFixed(0)}s)</span>`;
          } else if (job.status === 'processing') {
            statusBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">Processing ${job.progress || 0}%</span>`;
          } else if (job.status === 'queued') {
            statusBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">Queued</span>`;
          } else {
            statusBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-red-500/10 text-red-400 border border-red-500/20">Failed</span>`;
          }

          const hwBadge = `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono ${((job.device || 'cpu') === 'cuda') ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' : 'bg-slate-800 text-slate-400'}">${((job.device || 'cpu') === 'cuda') ? 'GPU' : 'CPU'}</span>`;

          div.innerHTML = `
            <div class="flex items-center gap-2 truncate mr-2">
              <span class="text-slate-200 font-medium truncate max-w-[180px]">${escapeHtml(job.filename)}</span>
              ${hwBadge}
              ${statusBadge}
            </div>
            <button type="button" class="btn-load-job px-2.5 py-1 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 border border-indigo-500/30 font-medium transition shrink-0">
              ${job.status === 'completed' ? 'Open' : 'Track'}
            </button>
          `;

          const btn = div.querySelector('.btn-load-job');
          btn.addEventListener('click', () => {
            currentJobId = job.id;
            localStorage.setItem('whisper_active_job', job.id);
            if (job.status === 'completed') {
              loadResults(job.id);
              statusCard.classList.add('hidden');
            } else {
              resultsCard.classList.add('hidden');
              startJobTracking(job.id);
            }
          });

          recentJobsList.appendChild(div);
        });
      } catch (e) {
        console.error("Failed to load recent jobs", e);
      }
    }

    btnRefreshJobs.addEventListener('click', refreshRecentJobs);

    // Immediate and robust page initialization
    function initStudio() {
      refreshRecentJobs();

      // Probe GPU hardware capabilities
      fetch('/health')
        .then(r => r.json())
        .then(h => {
          const optGpu = document.getElementById('optGpu');
          if (h && h.gpu_available) {
            gpuStatusBadge.innerHTML = `<span class="text-emerald-400 font-mono">● CUDA Active (${h.cuda_device_count} GPU)</span>`;
            if (optGpu) {
              optGpu.disabled = false;
              optGpu.className = "";
              optGpu.innerText = "⚡ GPU / CUDA (Active · float16)";
            }
            deviceSelect.value = "gpu";
          } else {
            gpuStatusBadge.innerHTML = `<span class="text-slate-500 font-mono">Host: CPU only (No GPU)</span>`;
            deviceSelect.value = "cpu";
            if (optGpu) {
              optGpu.disabled = true;
              optGpu.className = "text-slate-500";
              optGpu.innerText = "⚡ GPU / CUDA (No GPU detected)";
            }
          }
        })
        .catch(() => {});

      const savedJobId = localStorage.getItem('whisper_active_job');
      if (savedJobId) {
        fetch(`/api/v1/transcriptions/${savedJobId}`)
          .then(r => r.ok ? r.json() : null)
          .then(job => {
            if (job) {
              if (job.status === 'processing' || job.status === 'queued') {
                startJobTracking(savedJobId);
              } else if (job.status === 'completed') {
                currentJobId = savedJobId;
                loadResults(savedJobId);
              }
            }
          })
          .catch(() => {});
      }
    }

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', initStudio);
    } else {
      initStudio();
    }
  </script>
</body>
</html>
"""
