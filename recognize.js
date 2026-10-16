// Recognition interactions: audio, timed screen capture, camera frames, and file selection.
const toast = document.getElementById('recognize-toast');
let toastTimer;

function showToast(message) {
  if (!toast) return;

  toast.textContent = window.MUVYLocale?.t(message) ?? message;
  toast.classList.add('is-visible');

  window.clearTimeout(toastTimer);

  toastTimer = window.setTimeout(() => {
    toast.classList.remove('is-visible');
  }, 3200);
}

// Tablet navigation menu and preview actions.
const menuToggle = document.getElementById('recognize-menu-toggle');
const menuPanel = document.getElementById('recognize-menu-panel');

if (menuToggle && menuPanel) {
  menuToggle.addEventListener('click', () => {
    const willOpen = menuPanel.hidden;

    menuPanel.hidden = !willOpen;
    menuToggle.setAttribute('aria-expanded', String(willOpen));
  });

  document.addEventListener('click', (event) => {
    if (
      !menuPanel.hidden &&
      !menuPanel.contains(event.target) &&
      !menuToggle.contains(event.target)
    ) {
      menuPanel.hidden = true;
      menuToggle.setAttribute('aria-expanded', 'false');
    }
  });
}


// ---------------------------------------------------------
// Generic message buttons
// ---------------------------------------------------------

document.querySelectorAll('[data-message]').forEach((button) => {
  button.addEventListener('click', () => {
    showToast(button.dataset.message);
  });
});


// ---------------------------------------------------------
// API helpers
// ---------------------------------------------------------

async function identifyVideoFile(file) {
  if (!file) {
    throw new Error('No video file was provided.');
  }

  const apiBaseUrl =
    window.MUVY_API_BASE_URL ||
    (typeof API_BASE_URL === 'string' ? API_BASE_URL : '');

  if (!apiBaseUrl) {
    throw new Error('Movie identification service is not configured.');
  }

  const formData = new FormData();

  formData.append('file', file, file.name || 'muvy-video.webm');

  const response = await fetch(`${apiBaseUrl.replace(/\/+$/, '')}/identify`, {
    method: 'POST',
    headers: {
      'Accept-Language': window.MUVYLocale?.getTMDBLanguage() || 'en-US',
    },
    body: formData,
  });

  let data;

  try {
    data = await response.json();
  } catch {
    throw new Error(
      `MUVY API returned an invalid response (${response.status}).`
    );
  }

  if (!response.ok) {
    const message =
      typeof data?.detail === 'string'
        ? data.detail
        : `MUVY API request failed (${response.status}).`;

    throw new Error(message);
  }

  return data;
}


// ---------------------------------------------------------
// Recognition result UI
// ---------------------------------------------------------

function getPosterUrl(posterPath) {
  if (!posterPath) {
    return '';
  }

  if (posterPath.startsWith('http://') || posterPath.startsWith('https://')) {
    return posterPath;
  }

  return `https://image.tmdb.org/t/p/w500${posterPath}`;
}


function displayRecognitionResult(data) {
  if (!data || !data.matched || !data.movie) {
    showToast(
      data?.message || 'MUVY could not identify this movie.'
    );

    return;
  }

  const movie = data.movie;
  const match = data.match || {};
  const posterUrl = getPosterUrl(movie.poster_path);
  const genres = Array.isArray(movie.genres)
    ? movie.genres
        .map((genre) => typeof genre === 'string' ? genre : genre?.name)
        .filter(Boolean)
    : [];

  document.dispatchEvent(new CustomEvent('muvy:movie-identified', {
    detail: {
      title: movie.title || '',
      year: typeof movie.release_date === 'string'
        ? movie.release_date.slice(0, 4)
        : '',
      genres,
      timestamp: typeof match.timestamp_seconds === 'number'
        ? `${match.timestamp_seconds.toFixed(2)}s`
        : '',
      summary: movie.overview || '',
      posterUrl,
      providers: Array.isArray(data.providers) ? data.providers : [],
    },
  }));
}


// ---------------------------------------------------------
// Upload video
// ---------------------------------------------------------

// Recognition integrations can publish a result when a movie has been identified.
document.addEventListener('muvy:movie-identified', (event) => {
  const movie = event.detail;
  if (!movie || typeof movie.title !== 'string' || !movie.title.trim()) return;

  const preview = document.getElementById('match-preview');
  const poster = document.getElementById('match-poster');
  const metadata = [movie.year, Array.isArray(movie.genres) ? movie.genres.join(', ') : movie.genres]
    .filter(Boolean)
    .join(' · ');
  const providers = Array.isArray(movie.providers) ? movie.providers.filter((provider) => typeof provider === 'string') : [];

  document.getElementById('match-title').textContent = movie.title.trim();
  document.getElementById('match-metadata').textContent = metadata;
  document.getElementById('match-metadata').hidden = !metadata;
  document.getElementById('match-timestamp').textContent = movie.timestamp || '';
  document.getElementById('match-timestamp').hidden = !movie.timestamp;
  document.getElementById('match-summary').textContent = movie.summary || '';
  document.getElementById('match-summary').hidden = !movie.summary;
  poster.hidden = !movie.posterUrl;
  if (movie.posterUrl) {
    poster.src = movie.posterUrl;
    poster.alt = `${movie.title.trim()} poster`;
  } else {
    poster.removeAttribute('src');
    poster.alt = '';
  }
  const providerList = document.getElementById('match-provider-list');
  providerList.replaceChildren(...providers.map((provider) => {
    const item = document.createElement('span');
    item.textContent = provider;
    return item;
  }));
  document.getElementById('match-providers').hidden = providers.length === 0;
  preview.hidden = false;
});

// VIDEO UPLOAD: open the clip picker and report the selected file.
// This is the main section to find when wiring uploaded clips to identification.
const clipPicker = document.getElementById('clip-picker');
const uploadChoice = document.getElementById('upload-choice');

if (uploadChoice && clipPicker) {
  uploadChoice.addEventListener('click', () => {
    clipPicker.click();
  });

  clipPicker.addEventListener('change', async () => {
    const file = clipPicker.files && clipPicker.files[0];

    if (!file) {
      return;
    }

    await identifyUploadedMedia(file);
  });
}


async function identifyUploadedMedia(file) {
  const allowedExtensions = [
    '.mp4',
    '.mov',
    '.mkv',
    '.avi',
    '.webm',
    '.m4v',
    '.jpg',
    '.jpeg',
    '.png',
    '.webp',
  ];

  const fileName = file.name.toLowerCase();

  const isAllowed = allowedExtensions.some((extension) =>
    fileName.endsWith(extension)
  );

  if (!isAllowed) {
    showToast(
      'Unsupported format. Choose a supported video or JPG, PNG, or WEBP screenshot.'
    );

    return;
  }

  showToast(`Uploading ${file.name}...`);

  try {
    const data = await identifyVideoFile(file);

    displayRecognitionResult(data);

    if (data.matched && data.movie) {
      showToast(`Identified: ${data.movie.title}`);
    }
  } catch (error) {
    console.error('MUVY identification error:', error);

    showToast(
      error.message || 'Movie identification failed.'
    );
  }
}


// ---------------------------------------------------------
// Audio recognition
// ---------------------------------------------------------

// AUDIO RECOGNITION: microphone state, recording controls, and feedback.
const audioFeedback = document.getElementById('audio-feedback');
const audioStatus = document.getElementById('audio-status');
const stopAudioButton = document.getElementById('stop-audio');
const audioRecognitionButton =
  document.getElementById('audio-recognition-button');
const audioButtonLabel =
  document.getElementById('audio-button-label');

const audioButtonEqIcon =
  audioRecognitionButton?.querySelector('.audio-button-eq');

const audioButtonStopIcon =
  audioRecognitionButton?.querySelector('.audio-button-stop');

let audioStream = null;
let audioRecorder = null;
let audioTimer = null;
let audioChunks = [];


function setAudioButtonListening(isListening) {
  if (!audioRecognitionButton) return;

  audioRecognitionButton.classList.toggle(
    'is-listening',
    isListening
  );

  audioRecognitionButton.setAttribute(
    'aria-pressed',
    String(isListening)
  );

  if (audioButtonEqIcon) {
    audioButtonEqIcon.hidden = isListening;
  }

  if (audioButtonStopIcon) {
    audioButtonStopIcon.hidden = !isListening;
  }

  if (audioButtonLabel) {
    audioButtonLabel.textContent = window.MUVYLocale?.t(isListening
      ? 'Stop listening'
      : 'Start audio recognition');
  }
}


function stopAudioCapture() {
  window.clearTimeout(audioTimer);

  if (
    audioRecorder &&
    audioRecorder.state === 'recording'
  ) {
    audioRecorder.stop();
  }

  if (audioStream) {
    audioStream
      .getTracks()
      .forEach((track) => track.stop());
  }

  audioStream = null;

  if (stopAudioButton) {
    stopAudioButton.hidden = true;
  }

  setAudioButtonListening(false);
}


const startAudioRecognition = async () => {
  if (
    audioRecorder &&
    audioRecorder.state === 'recording'
  ) {
    stopAudioCapture();
    return;
  }

  if (
    !navigator.mediaDevices?.getUserMedia ||
    !window.MediaRecorder
  ) {
    if (audioFeedback) {
      audioFeedback.hidden = false;
    }

    if (audioStatus) {
      audioStatus.textContent =
        window.MUVYLocale?.t('Audio recording is not supported in this browser.');
    }

    return;
  }

  try {
    audioStream =
      await navigator.mediaDevices.getUserMedia({
        audio: true,
      });

    audioChunks = [];

    audioRecorder = new MediaRecorder(
      audioStream
    );

    audioRecorder.ondataavailable = (event) => {
      if (event.data.size) {
        audioChunks.push(event.data);
      }
    };

    audioRecorder.onstop = () => {
      if (audioStream) {
        audioStream
          .getTracks()
          .forEach((track) => track.stop());
      }

      audioStream = null;

      if (stopAudioButton) {
        stopAudioButton.hidden = true;
      }

      setAudioButtonListening(false);

      if (audioStatus) {
        audioStatus.textContent =
          window.MUVYLocale?.t('Audio captured. Audio recognition will be connected when the MUVY audio fingerprint service is available.');
      }
    };

    if (audioFeedback) {
      audioFeedback.hidden = false;
    }

    if (audioStatus) {
      audioStatus.textContent =
        window.MUVYLocale?.t('Listening for up to 10 seconds. Play the movie audio now.');
    }

    if (stopAudioButton) {
      stopAudioButton.hidden = false;
    }

    audioRecorder.start();

    setAudioButtonListening(true);

    audioTimer = window.setTimeout(
      stopAudioCapture,
      10000
    );

  } catch (error) {
    if (audioFeedback) {
      audioFeedback.hidden = false;
    }

    if (audioStatus) {
      audioStatus.textContent =
        window.MUVYLocale?.t(error.name === 'NotAllowedError'
          ? 'Microphone permission was not granted.'
          : 'Could not access the microphone.');
    }
  }
};


const audioChoice =
  document.getElementById('audio-choice');

if (audioChoice) {
  audioChoice.addEventListener(
    'click',
    startAudioRecognition
  );
}

if (audioRecognitionButton) {
  audioRecognitionButton.addEventListener(
    'click',
    () => {
      if (
        audioRecorder?.state === 'recording'
      ) {
        stopAudioCapture();
      } else {
        startAudioRecognition();
      }
    }
  );
}

if (stopAudioButton) {
  stopAudioButton.addEventListener(
    'click',
    stopAudioCapture
  );
}


// ---------------------------------------------------------
// Screen capture
// ---------------------------------------------------------

const captureDialog = document.getElementById('capture-dialog');
const captureOptions = document.getElementById('capture-options');
const captureLive = document.getElementById('capture-live');
const captureVideo = document.getElementById('capture-video');
const capturePreview = document.querySelector('.capture-preview');
const captureStatus = document.getElementById('capture-status');
const stopCaptureButton = document.getElementById('stop-capture');
const cameraRecordButton = document.getElementById('camera-record');
const identifyCaptureButton = document.getElementById('identify-capture');
let captureStream = null;
let mediaRecorder = null;
let captureTimer = null;
let recordedChunks = [];
let captureBlob = null;


function showCaptureError(message) {
  if (captureOptions) {
    captureOptions.hidden = true;
  }

  if (captureLive) {
    captureLive.hidden = false;
  }

  if (capturePreview) {
    capturePreview.classList.remove(
      'has-preview'
    );
  }

  if (captureStatus) {
    captureStatus.textContent = window.MUVYLocale?.t(message) ?? message;
  }

  if (stopCaptureButton) {
    stopCaptureButton.hidden = true;
  }

  if (cameraRecordButton) {
    cameraRecordButton.hidden = true;
  }

  if (identifyCaptureButton) {
    identifyCaptureButton.hidden = true;
  }
}


function showCaptureSession() {
  if (captureOptions) {
    captureOptions.hidden = true;
  }

  if (captureLive) {
    captureLive.hidden = false;
  }

  if (capturePreview) {
    capturePreview.classList.add(
      'has-preview'
    );
  }
}


function stopCaptureStream() {
  if (captureStream) {
    captureStream
      .getTracks()
      .forEach((track) => track.stop());
  }

  captureStream = null;

  if (captureVideo) {
    captureVideo.srcObject = null;
  }

  if (capturePreview) {
    capturePreview.classList.remove(
      'has-preview'
    );
  }
}


function resetCaptureDialog() {
  window.clearTimeout(captureTimer);

  if (
    mediaRecorder &&
    mediaRecorder.state === 'recording'
  ) {
    mediaRecorder.onstop = null;
    mediaRecorder.stop();
  }

  mediaRecorder = null;

  stopCaptureStream();

  recordedChunks = [];
  captureBlob = null;

  if (captureOptions) {
    captureOptions.hidden = false;
  }

  if (captureLive) {
    captureLive.hidden = true;
  }

  if (captureStatus) {
    captureStatus.textContent = '';
  }

  if (stopCaptureButton) {
    stopCaptureButton.hidden = true;
  }

  if (cameraRecordButton) {
    cameraRecordButton.hidden = true;
  }

  if (identifyCaptureButton) {
    identifyCaptureButton.hidden = true;
  }
}


function startCaptureRecording(statusMessage) {
  if (!window.MediaRecorder) {
    showCaptureError('Video recording is not supported in this browser.');
    return;
  }

  recordedChunks = [];
  captureBlob = null;
  const mimeType = typeof MediaRecorder.isTypeSupported === 'function'
    ? ['video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm', 'video/mp4']
      .find((type) => MediaRecorder.isTypeSupported(type))
    : undefined;
  const recorder = new MediaRecorder(captureStream, mimeType ? { mimeType } : undefined);
  mediaRecorder = recorder;
  recorder.ondataavailable = (event) => {
    if (event.data.size) recordedChunks.push(event.data);
  };
  recorder.onstop = () => {
    if (mediaRecorder !== recorder) return;
    window.clearTimeout(captureTimer);
    captureTimer = null;
    captureBlob = new Blob(recordedChunks, { type: recorder.mimeType || 'video/webm' });
    stopCaptureStream();
    stopCaptureButton.hidden = true;
    cameraRecordButton.hidden = true;
    identifyCaptureButton.hidden = false;
    captureStatus.textContent = window.MUVYLocale?.t('Clip captured. It is ready to identify.');
  };
  captureStream.getVideoTracks()[0]?.addEventListener('ended', () => {
    if (recorder.state === 'recording') recorder.stop();
  }, { once: true });
  recorder.start(1000);
  stopCaptureButton.querySelector('span').textContent = window.MUVYLocale?.t('Stop capture');
  stopCaptureButton.hidden = false;
  cameraRecordButton.hidden = true;
  captureStatus.textContent = window.MUVYLocale?.t(statusMessage);
  captureTimer = window.setTimeout(() => {
    if (recorder.state === 'recording') recorder.stop();
  }, 15000);
}


const screenChoice =
  document.getElementById('screen-choice');

if (screenChoice && captureDialog) {
  screenChoice.addEventListener('click', () => {
    resetCaptureDialog();
    captureDialog.showModal();
  });
}
document.getElementById('capture-close').addEventListener('click', () => captureDialog.close());
captureDialog.addEventListener('click', (event) => {
  if (event.target === captureDialog) captureDialog.close();
});
captureDialog.addEventListener('close', resetCaptureDialog);

document.getElementById('screen-record-option').addEventListener('click', async () => {
  if (!navigator.mediaDevices?.getDisplayMedia || !window.MediaRecorder) {
    showCaptureError('Screen recording is not supported here. You can upload a clip instead.');
    return;
  }
  try {
    captureStream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
    showCaptureSession();
    captureVideo.srcObject = captureStream;
    await captureVideo.play().catch(() => {});
    startCaptureRecording('Recording your selected screen. Stop after 10 to 15 seconds.');
  } catch (error) {
    stopCaptureStream();
    showCaptureError(error.name === 'NotAllowedError'
      ? 'Screen capture was cancelled. Choose an option to try again.'
      : 'Could not start screen capture. Choose an option to try again.');
  }
});

document.getElementById('back-camera-option').addEventListener('click', async () => {
  if (!navigator.mediaDevices?.getUserMedia) {
    showCaptureError('Camera access is not available in this browser.');
    return;
  }
  try {
    captureStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false });
    showCaptureSession();
    captureVideo.srcObject = captureStream;
    await captureVideo.play();
    stopCaptureButton.querySelector('span').textContent = window.MUVYLocale?.t('Close');
    stopCaptureButton.hidden = false;
    cameraRecordButton.hidden = false;
    captureStatus.textContent = window.MUVYLocale?.t('Point the back camera at the movie, then record a short clip.');
  } catch (error) {
    stopCaptureStream();
    showCaptureError(error.name === 'NotAllowedError'
      ? 'Camera permission was not granted. Choose an option to try again.'
      : 'Could not open the back camera. Choose an option to try again.');
  }
});

stopCaptureButton.addEventListener('click', () => {
  window.clearTimeout(captureTimer);
  if (mediaRecorder?.state === 'recording') {
    mediaRecorder.stop();
    return;
  }
  stopCaptureStream();
  stopCaptureButton.hidden = true;
  cameraRecordButton.hidden = true;
  captureStatus.textContent = window.MUVYLocale?.t('Camera closed.');
});

cameraRecordButton.addEventListener('click', () => {
  startCaptureRecording('Recording from the back camera. Keep the movie in frame for up to 15 seconds.');
});
identifyCaptureButton.addEventListener('click', async () => {
  if (!captureBlob) return;

  try {
    captureStatus.textContent = window.MUVYLocale?.t('Sending your clip to MUVY for identification...');
    const extension = captureBlob.type.includes('mp4') ? 'mp4' : 'webm';
    const file = new File([captureBlob], `muvy-capture.${extension}`, { type: captureBlob.type || 'video/webm' });
    const result = await identifyVideoFile(file);
    displayRecognitionResult(result);
    captureStatus.textContent = result?.matched && result?.movie?.title
      ? `Identified: ${result.movie.title}`
      : result?.message || 'No confident match found.';
  } catch (error) {
    console.error('Capture identification failed:', error);
    captureStatus.textContent = error.message || 'Movie identification failed.';
    showToast(captureStatus.textContent);
  }
});
