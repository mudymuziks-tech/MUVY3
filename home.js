// HOME PAGE: shared toast and action feedback.
const toast = document.getElementById('toast');
let toastTimer;

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

// HOME PAGE: open file pickers and report selected uploads.
document.querySelectorAll('[data-picker]').forEach((button) => {
  button.addEventListener('click', () => {
    window.location.href = 'recognize.html';
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
const captureFrameButton = document.getElementById('capture-frame');
const identifyCaptureButton = document.getElementById('identify-capture');
let captureStream = null;
let mediaRecorder = null;
let recordedChunks = [];
let captureBlob = null;

if (captureOptions && captureLive && capturePreview && captureVideo && captureStatus && stopCaptureButton && captureFrameButton && identifyCaptureButton) {
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
    captureFrameButton.hidden = true;
    identifyCaptureButton.hidden = true;
  }

  function stopCaptureStream() {
    if (captureStream) captureStream.getTracks().forEach((track) => track.stop());
    captureStream = null;
    captureVideo.srcObject = null;
    capturePreview.classList.remove('has-preview');
  }

  function resetCaptureDialog() {
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
    captureFrameButton.hidden = true;
    identifyCaptureButton.hidden = true;
  }

  document.getElementById('camera-options-button').addEventListener('click', () => {
    window.location.href = 'recognize.html';
  });
  document.getElementById('capture-close').addEventListener('click', () => captureDialog.close());
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
    recordedChunks = [];
    captureBlob = null;
    const mimeType = ['video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm']
      .find((type) => MediaRecorder.isTypeSupported(type));
    const recorder = new MediaRecorder(captureStream, mimeType ? { mimeType } : undefined);
    mediaRecorder = recorder;
    recorder.ondataavailable = (event) => {
      if (event.data.size) recordedChunks.push(event.data);
    };
    recorder.onstop = () => {
      if (mediaRecorder !== recorder) return;
      captureBlob = new Blob(recordedChunks, { type: recorder.mimeType || 'video/webm' });
      stopCaptureStream();
      stopCaptureButton.hidden = true;
      identifyCaptureButton.hidden = false;
      captureStatus.textContent = window.MUVYLocale?.t('Screen clip captured. It is ready to identify.');
    };
    captureStream.getVideoTracks()[0]?.addEventListener('ended', () => {
      if (mediaRecorder?.state === 'recording') mediaRecorder.stop();
    }, { once: true });
    recorder.start(1000);
    stopCaptureButton.textContent = window.MUVYLocale?.t('Stop capture');
    stopCaptureButton.hidden = false;
    captureStatus.textContent = window.MUVYLocale?.t('Recording your selected screen. Stop when you have captured the scene.');
  } catch (error) {
    stopCaptureStream();
    showCaptureError(error.name === 'NotAllowedError'
      ? 'Screen capture was cancelled. Choose an option to try again.'
      : 'Could not start screen capture. Choose an option to try again.');
  }
});

  // HOME CAPTURE: back-camera flow and still-frame capture.
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
      stopCaptureButton.textContent = window.MUVYLocale?.t('Close');
      stopCaptureButton.hidden = false;
      captureFrameButton.hidden = false;
      captureStatus.textContent = window.MUVYLocale?.t('Point the back camera at the movie, then capture a frame.');
    } catch (error) {
      stopCaptureStream();
      showCaptureError(error.name === 'NotAllowedError'
        ? 'Camera permission was not granted. Choose an option to try again.'
        : 'Could not open the back camera. Choose an option to try again.');
    }
  });

  stopCaptureButton.addEventListener('click', () => {
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
      identifyCaptureButton.hidden = false;
      captureStatus.textContent = window.MUVYLocale?.t('Frame captured. It is ready to identify.');
    }, 'image/jpeg', .92);
  });

  identifyCaptureButton.addEventListener('click', () => {
    if (!captureBlob) return;
    captureStatus.textContent = window.MUVYLocale?.t('The capture is ready, but movie identification is not connected yet.');
  });
}
