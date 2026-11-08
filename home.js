// HOME PAGE: shared toast and action feedback.
const toast = document.getElementById('toast');
let toastTimer;

async function identifyVideoFile(file) {
  if (!file) throw new Error('No video file was provided.');
  const apiBaseUrl = window.MUVY_API_BASE_URL;
  if (!apiBaseUrl) throw new Error('Movie identification service is not configured.');

  const formData = new FormData();
  formData.append('file', file, file.name || 'muvy-video.webm');

  const response = await fetch(`${apiBaseUrl.replace(/\/+$/, '')}/identify`, {
    method: 'POST',
    headers: {
      'Accept-Language': 'en-US',
    },
    body: formData,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(typeof data?.detail === 'string' ? data.detail : `MUVY API request failed (${response.status}).`);
  }

  return data;
}

function showToast(message) {
  if (!toast) return;

  toast.textContent = window.MUVYLocale?.t(message) ?? message;
  toast.classList.add('is-visible');
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove('is-visible'), 3000);
}

document.querySelectorAll('[data-message]').forEach((button) => {
  button.addEventListener('click', () => showToast(button.dataset.message));
});

document.querySelectorAll('[data-open-recognition]').forEach((button) => {
  button.addEventListener('click', () => {
    window.location.href = 'recognize.html';
  });
});

// HOME PAGE: open file pickers and report selected uploads.
document.querySelectorAll('[data-picker]').forEach((button) => {
  button.addEventListener('click', () => {
    const picker = document.getElementById(button.dataset.picker);
    if (picker) picker.click();
  });
});

document.querySelectorAll('input[type="file"]').forEach((input) => {
  input.addEventListener('change', async () => {
    const file = input.files?.[0];
    if (!file) return;

    try {
      showToast(`Uploading ${file.name}...`);
      const result = await identifyVideoFile(file);

      if (result?.matched && result?.movie?.title) {
        showToast(`Identified: ${result.movie.title}`);
      } else {
        showToast(result?.message || 'No confident match found.');
      }
    } catch (error) {
      console.error('MUVY identification failed:', error);
      showToast(error.message || 'Movie identification failed.');
    }
  });
});

// HOME PAGE: movie card placeholder actions.
document.querySelectorAll('.movie-card').forEach((card) => {
  card.addEventListener('click', (event) => {
    event.preventDefault();
    showToast(`${card.dataset.title} details are coming soon.`);
  });
});

// HOME PAGE: expandable movie search and account-based greeting.
const searchToggle = document.getElementById('search-toggle');
const searchRow = document.getElementById('search-row');
const searchInput = document.getElementById('movie-search');

if (searchToggle && searchRow && searchInput) {
  if (window.matchMedia('(min-width: 1000px)').matches) searchRow.hidden = false;
  searchToggle.addEventListener('click', () => {
    const opening = searchRow.hidden;
    searchRow.hidden = !opening;
    searchToggle.setAttribute('aria-expanded', String(opening));
    if (opening) searchInput.focus();
  });
  searchRow.addEventListener('submit', (event) => {
    event.preventDefault();
    const query = searchInput.value.trim();
    if (query) showToast(`Search for ${query} will be available soon.`);
  });
}

const greetingTitle = document.getElementById('greeting-title');
let greetingTimer;

function updateGreeting() {
  if (!greetingTitle) return;

  const currentAccount = window.MUVYAuth?.getSession();
  const emailName = currentAccount?.email?.split('@')[0].replace(/[._-]+/g, ' ').trim();
  const displayName = currentAccount?.name?.trim() || emailName;
  const firstName = displayName?.split(/\s+/)[0] || 'MUDY';
  const now = new Date();
  const timeGreeting = now.getHours() < 12 ? 'Good morning' :
    now.getHours() < 17 ? 'Good afternoon' : 'Good evening';

  greetingTitle.textContent = `${window.MUVYLocale?.t(timeGreeting) ?? timeGreeting}, ${firstName}`;

  const millisecondsUntilNextHour =
    (60 - now.getMinutes()) * 60_000 - now.getSeconds() * 1000 - now.getMilliseconds();
  window.clearTimeout(greetingTimer);
  greetingTimer = window.setTimeout(updateGreeting, millisecondsUntilNextHour + 50);
}

updateGreeting();
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) updateGreeting();
});

// HOME CAPTURE: shared dialog, preview, and stream cleanup helpers.
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

function showCaptureSession() {
  captureOptions.hidden = true;
  captureLive.hidden = false;
  capturePreview.classList.add('has-preview');
}

function showCaptureError(message) {
  captureOptions.hidden = true;
  captureLive.hidden = false;
  capturePreview.classList.remove('has-preview');
  captureStatus.textContent = window.MUVYLocale?.t(message) ?? message;
  stopCaptureButton.hidden = true;
  cameraRecordButton.hidden = true;
  identifyCaptureButton.hidden = true;
}

function stopCaptureStream() {
  window.clearTimeout(captureTimer);
  captureTimer = null;

  if (captureStream) {
    captureStream.getTracks().forEach((track) => track.stop());
  }

  captureStream = null;
  captureVideo.srcObject = null;
  capturePreview.classList.remove('has-preview');
}

function resetCaptureDialog() {
  window.clearTimeout(captureTimer);
  captureTimer = null;

  if (mediaRecorder && mediaRecorder.state === 'recording') {
    mediaRecorder.onstop = null;
    mediaRecorder.stop();
  }

  mediaRecorder = null;
  stopCaptureStream();
  recordedChunks = [];
  captureBlob = null;

  captureOptions.hidden = false;
  captureLive.hidden = true;
  captureStatus.textContent = '';
  stopCaptureButton.hidden = true;
  cameraRecordButton.hidden = true;
  identifyCaptureButton.hidden = true;
}

function startCaptureRecording(statusMessage) {
  if (!window.MediaRecorder) {
    stopCaptureStream();
    showCaptureError('Video recording is not supported in this browser.');
    return;
  }

  if (!captureStream?.getVideoTracks().length) {
    showCaptureError('No video stream is available to record.');
    return;
  }

  recordedChunks = [];
  captureBlob = null;

  const mimeType = typeof MediaRecorder.isTypeSupported === 'function'
    ? [
        'video/webm;codecs=vp9',
        'video/webm;codecs=vp8',
        'video/webm',
        'video/mp4'
      ].find((type) => MediaRecorder.isTypeSupported(type))
    : undefined;

  let recorder;

  try {
    recorder = new MediaRecorder(
      captureStream,
      mimeType ? { mimeType } : undefined
    );
  } catch (error) {
    stopCaptureStream();
    showCaptureError('Could not start video recording in this browser.');
    return;
  }

  mediaRecorder = recorder;

  recorder.ondataavailable = (event) => {
    if (event.data.size) recordedChunks.push(event.data);
  };

  recorder.onerror = () => {
    showCaptureError('An error occurred while recording the clip.');
    stopCaptureStream();
  };

  recorder.onstop = () => {
    if (mediaRecorder !== recorder) return;

    window.clearTimeout(captureTimer);
    captureTimer = null;

    captureBlob = new Blob(recordedChunks, {
      type: recorder.mimeType || 'video/webm'
    });

    stopCaptureStream();
    stopCaptureButton.hidden = true;
    cameraRecordButton.hidden = true;
    identifyCaptureButton.hidden = captureBlob.size === 0;

    captureStatus.textContent = captureBlob.size
      ? 'Clip captured. It is ready to identify.'
      : 'The recording was empty. Please try again.';
  };

  captureStream.getVideoTracks()[0]?.addEventListener('ended', () => {
    if (recorder.state === 'recording') recorder.stop();
  }, { once: true });

  try {
    recorder.start(1000);
  } catch (error) {
    mediaRecorder = null;
    stopCaptureStream();
    showCaptureError('Could not start video recording.');
    return;
  }

  stopCaptureButton.textContent =
    window.MUVYLocale?.t('Stop capture') ?? 'Stop capture';

  stopCaptureButton.hidden = false;
  cameraRecordButton.hidden = true;

  captureStatus.textContent =
    window.MUVYLocale?.t(statusMessage) ?? statusMessage;

  captureTimer = window.setTimeout(() => {
    if (recorder.state === 'recording') recorder.stop();
  }, 15000);
}

document.getElementById('camera-options-button').addEventListener('click', () => {
  resetCaptureDialog();
  captureDialog.showModal();
});

document.getElementById('capture-close').addEventListener('click', () => {
  captureDialog.close();
});

captureDialog.addEventListener('click', (event) => {
  if (event.target === captureDialog) captureDialog.close();
});

captureDialog.addEventListener('close', resetCaptureDialog);

// HOME CAPTURE: screen recording flow.
document.getElementById('screen-record-option').addEventListener('click', async () => {
  if (!navigator.mediaDevices?.getDisplayMedia || !window.MediaRecorder) {
    showCaptureError('Screen recording is not supported in this browser. Try uploading a clip instead.');
    return;
  }

  try {
    captureStream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
    showCaptureSession();
    captureVideo.srcObject = captureStream;
    await captureVideo.play().catch(() => {});
    startCaptureRecording('Recording your selected screen. Stop when you have captured the scene.');
  } catch (error) {
    stopCaptureStream();
    showCaptureError(error.name === 'NotAllowedError'
      ? 'Screen capture was cancelled. Choose an option to try again.'
      : 'Could not start screen capture. Choose an option to try again.');
  }
});

// HOME CAPTURE: back-camera recording.
document.getElementById('back-camera-option').addEventListener('click', async () => {
  if (!navigator.mediaDevices?.getUserMedia) {
    showCaptureError('Camera access is not available in this browser.');
    return;
  }

  try {
    captureStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: 'environment' } },
      audio: false
    });

    showCaptureSession();
    captureVideo.srcObject = captureStream;
    await captureVideo.play();

    stopCaptureButton.textContent =
      window.MUVYLocale?.t('Close') ?? 'Close';

    stopCaptureButton.hidden = false;
    cameraRecordButton.hidden = false;

    captureStatus.textContent =
      'Point the back camera at the movie, then record a short clip.';
  } catch (error) {
    stopCaptureStream();

    showCaptureError(
      error.name === 'NotAllowedError'
        ? 'Camera permission was not granted. Choose an option to try again.'
        : 'Could not open the back camera. Choose an option to try again.'
    );
  }
});

stopCaptureButton.addEventListener('click', () => {
  if (mediaRecorder?.state === 'recording') {
    mediaRecorder.stop();
    return;
  }

  stopCaptureStream();
  stopCaptureButton.hidden = true;
  cameraRecordButton.hidden = true;
  captureStatus.textContent = 'Camera closed.';
});

cameraRecordButton.addEventListener('click', () => {
  startCaptureRecording(
    'Recording from the back camera. Keep the movie in frame for up to 15 seconds.'
  );
});

identifyCaptureButton.addEventListener('click', async () => {
  if (!captureBlob) return;

  try {
    captureStatus.textContent = 'Sending your clip to MUVY for identification...';

    const extension = captureBlob.type.includes('mp4') ? 'mp4' : 'webm';

    const file = new File(
      [captureBlob],
      `muvy-capture.${extension}`,
      { type: captureBlob.type || 'video/webm' }
    );

    const result = await identifyVideoFile(file);

    if (result?.matched && result?.movie?.title) {
      showToast(`Identified: ${result.movie.title}`);
      captureStatus.textContent = `Identified: ${result.movie.title}`;
    } else {
      const message = result?.message || 'No confident match found.';
      showToast(message);
      captureStatus.textContent = message;
    }
  } catch (error) {
    console.error('Capture identification failed:', error);

    const message = error.message || 'Movie identification failed.';
    showToast(message);
    captureStatus.textContent = message;
  }
});
