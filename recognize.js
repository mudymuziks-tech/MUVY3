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

function getApiBaseUrl() {
  const localFrontend = ['localhost', '127.0.0.1'].includes(window.location.hostname);
  const apiBaseUrl =
    window.MUVY_API_BASE_URL ||
    (typeof API_BASE_URL === 'string' ? API_BASE_URL : '') ||
    (localFrontend ? 'http://127.0.0.1:8000' : '');

  if (!apiBaseUrl) {
    throw new Error('Movie identification service is not configured.');
  }

  return apiBaseUrl.replace(/\/+$/, '');
}

async function readApiResponse(response) {
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

const identificationScreen = document.getElementById('identification-screen');
const cancelIdentificationButton = document.getElementById('cancel-identification');
let activeIdentificationController = null;

function setIdentifying(isIdentifying) {
  if (identificationScreen) identificationScreen.hidden = !isIdentifying;
  document.body.classList.toggle('is-identifying', isIdentifying);
}

if (cancelIdentificationButton) {
  cancelIdentificationButton.addEventListener('click', () => {
    activeIdentificationController?.abort();
  });
}

// Time budget for a single identification request. The backend decodes the
// clip and queries the fingerprint database, so allow a generous window but
// never let a hung or cold-start connection block the interface indefinitely.
const IDENTIFY_TIMEOUT_MS = 90_000;

async function identifyVideoFile(file, signal) {
  if (!file) {
    throw new Error('No video file was provided.');
  }

  const apiBaseUrl = getApiBaseUrl();

  const formData = new FormData();
  formData.append('file', file, file.name || 'muvy-video.webm');

  // Combine the caller's cancel signal with an internal timeout so the request
  // can be aborted either by the user (Cancel) or by a stuck connection.
  const controller = new AbortController();
  const timer = window.setTimeout(() => {
    controller.abort(
      new DOMException('The identification service took too long.', 'TimeoutError')
    );
  }, IDENTIFY_TIMEOUT_MS);

  const forwardAbort = () => controller.abort(signal?.reason);
  if (signal) {
    if (signal.aborted) {
      controller.abort(signal.reason);
    } else {
      signal.addEventListener('abort', forwardAbort, { once: true });
    }
  }

  try {
    const response = await fetch(`${apiBaseUrl}/identify`, {
      method: 'POST',
      headers: {
        'Accept-Language': window.MUVYLocale?.getTMDBLanguage() || 'en-US',
      },
      body: formData,
      signal: controller.signal,
    });

    return await readApiResponse(response);
  } finally {
    window.clearTimeout(timer);
    signal?.removeEventListener('abort', forwardAbort);
  }
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
    const matchResult = document.getElementById('match-result');
    const unmatchedPanel = document.getElementById('unmatched-panel');

    if (matchResult) matchResult.hidden = true;
    document.querySelector('.recognize-main')?.classList.remove('is-result');
    document.getElementById('recognize-page-title').textContent = 'Recognize';
    if (unmatchedPanel) {
      unmatchedPanel.hidden = false;
      unmatchedPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    showToast(
      data?.message || 'MUVY could not identify this movie.'
    );

    return;
  }

  const unmatchedPanel = document.getElementById('unmatched-panel');
  if (unmatchedPanel) unmatchedPanel.hidden = true;

  const movie = data.movie;
  const match = data.match || {};
  const genres = Array.isArray(movie.genres)
    ? movie.genres
        .map((genre) => typeof genre === 'string' ? genre : genre?.name)
        .filter(Boolean)
    : [];

  const result = document.getElementById('match-result');
  const title = movie.title || 'Unknown title';
  const year = typeof movie.release_date === 'string'
    ? movie.release_date.slice(0, 4)
    : '';
  const runtime = Number.isFinite(movie.runtime) && movie.runtime > 0
    ? `${Math.floor(movie.runtime / 60)}h ${movie.runtime % 60}m`
    : '';
  const metadata = [year, ...genres, runtime].filter(Boolean).join(' · ');
  const backdropUrl = getPosterUrl(movie.backdrop_path || movie.poster_path);

  document.getElementById('match-title').textContent = title;
  document.getElementById('match-metadata').textContent = metadata;
  document.getElementById('match-metadata').hidden = !metadata;

  const backdrop = document.getElementById('match-backdrop');
  backdrop.hidden = !backdropUrl;
  if (backdropUrl) {
    backdrop.src = backdropUrl.replace('/w500/', '/original/');
    backdrop.alt = '';
  } else {
    backdrop.removeAttribute('src');
    backdrop.alt = '';
  }

  const rating = document.getElementById('match-rating');
  const ratingValue = Number(movie.vote_average);
  rating.hidden = !Number.isFinite(ratingValue) || ratingValue <= 0;
  const voteCount = Number(movie.vote_count);
  const ratingCount = Number.isFinite(voteCount) && voteCount > 0
    ? ` · ${new Intl.NumberFormat(undefined, { notation: 'compact' }).format(voteCount)} votes`
    : '';
  rating.textContent = rating.hidden ? '' : `★ ${ratingValue.toFixed(1)} / 10${ratingCount}`;

  const timestamp = document.getElementById('match-timestamp');
  timestamp.textContent = typeof match.timestamp_seconds === 'number'
    ? `Matched at ${match.timestamp_seconds.toFixed(1)}s`
    : '';
  timestamp.hidden = !timestamp.textContent;

  const overview = document.getElementById('match-summary');
  overview.textContent = movie.overview || '';
  overview.hidden = !overview.textContent;
  result.hidden = false;
  document.getElementById('unmatched-panel').hidden = true;
  document.querySelector('.recognize-main').classList.add('is-result');
  document.getElementById('recognize-page-title').textContent = 'Recognition Result';
  document.getElementById('match-title').focus({ preventScroll: true });
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

const catalogSearchForm = document.getElementById('catalog-search-form');
const catalogSearchInput = document.getElementById('catalog-search-input');
const catalogSearchButton = document.getElementById('catalog-search-button');
const catalogStatus = document.getElementById('catalog-status');
const catalogResults = document.getElementById('catalog-results');

if (
  catalogSearchForm &&
  catalogSearchInput &&
  catalogSearchButton &&
  catalogStatus &&
  catalogResults
) {
  catalogSearchForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    const query = catalogSearchInput.value.trim();
    if (query.length < 2) return;

    catalogSearchButton.disabled = true;
    catalogStatus.textContent = 'Searching TMDB...';
    catalogResults.replaceChildren();

    try {
      const url = new URL(`${getApiBaseUrl()}/tmdb/search`);
      url.searchParams.set('q', query);
      const response = await fetch(url, {
        headers: {
          'Accept-Language': window.MUVYLocale?.getTMDBLanguage() || 'en-US',
        },
      });
      const movies = await readApiResponse(response);

      if (!Array.isArray(movies) || movies.length === 0) {
        catalogStatus.textContent = 'No TMDB titles matched that search. Try another title.';
        return;
      }

      catalogStatus.textContent = `${movies.length} TMDB result${movies.length === 1 ? '' : 's'}. Choose a movie to suggest it for review.`;

      for (const movie of movies) {
        if (!Number.isInteger(movie.id) || typeof movie.title !== 'string') continue;

        const result = document.createElement('article');
        result.className = 'catalog-result';

        if (movie.poster_path) {
          const poster = document.createElement('img');
          poster.src = getPosterUrl(movie.poster_path);
          poster.alt = '';
          poster.loading = 'lazy';
          result.append(poster);
        }

        const details = document.createElement('div');
        details.className = 'catalog-result-details';

        const title = document.createElement('strong');
        title.textContent = movie.title;
        details.append(title);

        if (movie.release_date) {
          const year = document.createElement('small');
          year.textContent = movie.release_date.slice(0, 4);
          details.append(year);
        }

        if (movie.overview) {
          const overview = document.createElement('p');
          overview.textContent = movie.overview;
          details.append(overview);
        }

        const suggestButton = document.createElement('button');
        suggestButton.type = 'button';
        suggestButton.className = 'catalog-suggest-button';
        suggestButton.textContent = 'Suggest for review';
        suggestButton.addEventListener('click', async () => {
          suggestButton.disabled = true;
          catalogStatus.textContent = `Sending "${movie.title}" for catalog review...`;
          const controller = new AbortController();
          const timeout = window.setTimeout(() => controller.abort(), 20000);

          try {
            const submission = await fetch(`${getApiBaseUrl()}/catalog-requests`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ tmdb_id: movie.id }),
              signal: controller.signal,
            });
            const data = await readApiResponse(submission);
            suggestButton.textContent = data.already_submitted ? 'Already suggested' : 'Suggestion sent';
            catalogStatus.textContent = data.message;
          } catch (error) {
            suggestButton.disabled = false;
            catalogStatus.textContent = error.name === 'AbortError'
              ? 'The request timed out. Check your connection and try again; duplicate suggestions are safe.'
              : error.message || 'Could not submit the suggestion.';
          } finally {
            window.clearTimeout(timeout);
          }
        });

        result.append(details, suggestButton);
        catalogResults.append(result);
      }
    } catch (error) {
      catalogStatus.textContent = error.message || 'Movie search failed. Please try again.';
    } finally {
      catalogSearchButton.disabled = false;
    }
  });
}


// ---------------------------------------------------------
// Upload video
// ---------------------------------------------------------

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

    await identifyUploadedVideo(file);
  });
}


async function identifyUploadedVideo(file) {
  const allowedExtensions = [
    '.mp4',
    '.mov',
    '.mkv',
    '.avi',
    '.webm',
    '.m4v',
  ];

  const fileName = file.name.toLowerCase();

  const isAllowed = allowedExtensions.some((extension) =>
    fileName.endsWith(extension)
  );

  if (!isAllowed) {
    showToast(
      'Unsupported video format. Please select MP4, MOV, MKV, AVI, WEBM or M4V.'
    );

    return;
  }

  // Guard against empty or oversized uploads before touching the network. A
  // 10–15 second clip is normally only a few megabytes.
  const MAX_UPLOAD_BYTES = 100 * 1024 * 1024;

  if (file.size === 0) {
    showToast('That file is empty. Please choose a valid video clip.');
    return;
  }

  if (file.size > MAX_UPLOAD_BYTES) {
    showToast('That clip is too large. Please upload a short clip under 100 MB.');
    return;
  }

  const controller = new AbortController();
  activeIdentificationController = controller;
  setIdentifying(true);
  try {
    const data = await identifyVideoFile(file, controller.signal);

    displayRecognitionResult(data);

    if (data.matched && data.movie) {
      showToast(`Identified: ${data.movie.title}`);
    }
  } catch (error) {
    if (error.name === 'AbortError') {
      showToast('Identification cancelled.');
      return;
    }

    if (error.name === 'TimeoutError') {
      showToast('The recognition service took too long to respond. Please try again.');
      return;
    }

    // fetch() rejects with a TypeError when the backend is unreachable
    // (network down, wrong URL, or blocked by CORS).
    if (
      error instanceof TypeError ||
      /failed to fetch|networkerror|load failed/i.test(error.message || '')
    ) {
      showToast(
        'Cannot reach the recognition service. Check your connection and the configured API URL.'
      );
      return;
    }

    console.error('MUVY identification error:', error);

    showToast(
      error.message || 'Movie identification failed.'
    );
  } finally {
    if (activeIdentificationController === controller) {
      activeIdentificationController = null;
      setIdentifying(false);
    }
  }
}

document.getElementById('match-result-back').addEventListener('click', () => {
  document.getElementById('match-result').hidden = true;
  document.querySelector('.recognize-main').classList.remove('is-result');
  document.getElementById('recognize-page-title').textContent = 'Recognize';
  document.getElementById('upload-choice').focus({ preventScroll: true });
});


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


async function identifyAudioClip(blob) {
  const controller = new AbortController();
  activeIdentificationController = controller;
  setIdentifying(true);

  const timer = window.setTimeout(() => {
    controller.abort(
      new DOMException('The audio identification service took too long.', 'TimeoutError')
    );
  }, 90_000);

  try {
    const apiBaseUrl = getApiBaseUrl();
    const formData = new FormData();
    const file = new File([blob], 'muvy-audio.webm', {
      type: blob.type || 'audio/webm',
    });
    formData.append('file', file, file.name);

    const response = await fetch(`${apiBaseUrl}/identify-audio`, {
      method: 'POST',
      headers: {
        'Accept-Language': window.MUVYLocale?.getTMDBLanguage() || 'en-US',
      },
      body: formData,
      signal: controller.signal,
    });

    const data = await readApiResponse(response);
    displayRecognitionResult(data);

    if (data.matched && data.movie) {
      showToast(`Identified: ${data.movie.title}`);
    }
  } catch (error) {
    if (error.name === 'AbortError') {
      showToast('Identification cancelled.');
      return;
    }

    if (error.name === 'TimeoutError') {
      showToast('The audio recognition service took too long to respond. Please try again.');
      return;
    }

    if (
      error instanceof TypeError ||
      /failed to fetch|networkerror|load failed/i.test(error.message || '')
    ) {
      showToast(
        'Cannot reach the recognition service. Check your connection and the configured API URL.'
      );
      return;
    }

    console.error('MUVY audio identification error:', error);
    showToast(error.message || 'Audio identification failed.');
  } finally {
    window.clearTimeout(timer);
    if (activeIdentificationController === controller) {
      activeIdentificationController = null;
      setIdentifying(false);
    }
  }
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

      if (audioFeedback) {
        audioFeedback.hidden = true;
      }

      setAudioButtonListening(false);

      if (!audioChunks.length) {
        if (audioFeedback) audioFeedback.hidden = false;
        if (audioStatus) {
          audioStatus.textContent =
            window.MUVYLocale?.t('No audio was captured. Please try again.');
        }
        return;
      }

      const audioBlob = new Blob(audioChunks, {
        type: audioRecorder.mimeType || 'audio/webm',
      });
      audioChunks = [];

      identifyAudioClip(audioBlob);
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
const captureFrameButton = document.getElementById('capture-frame');
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

  if (captureFrameButton) {
    captureFrameButton.hidden = true;
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

  if (captureFrameButton) {
    captureFrameButton.hidden = true;
  }

  if (identifyCaptureButton) {
    identifyCaptureButton.hidden = true;
  }
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
    recordedChunks = [];
    captureBlob = null;
    const mimeType = ['video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm']
      .find((type) => MediaRecorder.isTypeSupported(type));
    const recorder = new MediaRecorder(captureStream, mimeType ? { mimeType } : undefined);
    mediaRecorder = recorder;
    recorder.ondataavailable = (event) => { if (event.data.size) recordedChunks.push(event.data); };
    recorder.onstop = () => {
      if (mediaRecorder !== recorder) return;
      captureBlob = new Blob(recordedChunks, { type: recorder.mimeType || 'video/webm' });
      stopCaptureStream();
      stopCaptureButton.hidden = true;
      identifyCaptureButton.hidden = false;
      captureStatus.textContent = window.MUVYLocale?.t('Screen clip captured. It is ready to identify.');
    };
    captureStream.getVideoTracks()[0]?.addEventListener('ended', () => {
      if (recorder.state === 'recording') recorder.stop();
    }, { once: true });
    recorder.start(1000);
    stopCaptureButton.querySelector('span').textContent = window.MUVYLocale?.t('Stop capture');
    stopCaptureButton.hidden = false;
    captureStatus.textContent = window.MUVYLocale?.t('Recording your selected screen. Stop after 10 to 15 seconds.');
    captureTimer = window.setTimeout(() => {
      if (recorder.state === 'recording') recorder.stop();
    }, 15000);
  } catch (error) {
    stopCaptureStream();
    showCaptureError(error.name === 'NotAllowedError'
      ? 'Screen capture was cancelled. Choose an option to try again.'
      : 'Could not start screen capture. Choose an option to try again.');
  }
});

document.getElementById('back-camera-option').addEventListener('click', async () => {
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    showCaptureError('Camera recording is not available in this browser. You can upload a clip instead.');
    return;
  }
  try {
    captureStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: 'environment' } },
      audio: false,
    });
    showCaptureSession();
    captureVideo.srcObject = captureStream;
    await captureVideo.play().catch(() => {});
    recordedChunks = [];
    captureBlob = null;
    const mimeType = ['video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm']
      .find((type) => MediaRecorder.isTypeSupported(type));
    const recorder = new MediaRecorder(captureStream, mimeType ? { mimeType } : undefined);
    mediaRecorder = recorder;
    recorder.ondataavailable = (event) => { if (event.data.size) recordedChunks.push(event.data); };
    recorder.onstop = () => {
      if (mediaRecorder !== recorder) return;
      captureBlob = new Blob(recordedChunks, { type: recorder.mimeType || 'video/webm' });
      stopCaptureStream();
      stopCaptureButton.hidden = true;
      captureFrameButton.hidden = true;
      identifyCaptureButton.hidden = false;
      captureStatus.textContent = window.MUVYLocale?.t('Camera clip captured. It is ready to identify.');
    };
    captureStream.getVideoTracks()[0]?.addEventListener('ended', () => {
      if (recorder.state === 'recording') recorder.stop();
    }, { once: true });
    recorder.start(1000);
    stopCaptureButton.querySelector('span').textContent = window.MUVYLocale?.t('Stop recording');
    stopCaptureButton.hidden = false;
    captureFrameButton.hidden = true;
    captureStatus.textContent = window.MUVYLocale?.t('Recording from the back camera. Keep it steady on the movie for 10 to 15 seconds.');
    captureTimer = window.setTimeout(() => {
      if (recorder.state === 'recording') recorder.stop();
    }, 15000);
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
  captureFrameButton.hidden = true;
  captureStatus.textContent = window.MUVYLocale?.t('Camera closed.');
});

captureFrameButton.addEventListener('click', () => {
  if (!captureVideo.videoWidth || !captureVideo.videoHeight) return;
  const canvas = document.createElement('canvas');
  canvas.width = captureVideo.videoWidth;
  canvas.height = captureVideo.videoHeight;
  canvas.getContext('2d').drawImage(captureVideo, 0, 0);
  canvas.toBlob((blob) => {
    captureBlob = blob;
    stopCaptureStream();
    stopCaptureButton.hidden = true;
    captureFrameButton.hidden = true;
    identifyCaptureButton.hidden = true;
    captureStatus.textContent = window.MUVYLocale?.t('Frame captured. Still-image recognition is not available yet.');
  }, 'image/jpeg', .92);
});
identifyCaptureButton.addEventListener('click', async () => {
  if (!captureBlob) return;

  if (captureBlob.type.startsWith('image/')) {
    showToast('Still-image recognition is not available yet. Capture a 10 to 15 second screen clip instead.');
    return;
  }

  identifyCaptureButton.disabled = true;

  try {
    const file = new File([captureBlob], 'muvy-capture.webm', {
      type: captureBlob.type || 'video/webm',
    });
    captureDialog.close();
    await identifyUploadedVideo(file);
  } catch (error) {
    captureStatus.textContent = error.message || 'Movie identification failed.';
  } finally {
    identifyCaptureButton.disabled = false;
  }
});
