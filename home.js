const toast = document.getElementById('toast');
let toastTimer;

function showToast(message) {
  toast.textContent = message;
  toast.classList.add('is-visible');
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove('is-visible'), 3000);
}

document.querySelectorAll('[data-message]').forEach((button) => {
  button.addEventListener('click', () => showToast(button.dataset.message));
});

document.querySelectorAll('[data-picker]').forEach((button) => {
  button.addEventListener('click', () => document.getElementById(button.dataset.picker).click());
});

document.querySelectorAll('input[type="file"]').forEach((input) => {
  input.addEventListener('change', () => {
    const file = input.files && input.files[0];
    if (file) showToast(`${file.name} selected. Movie recognition is not connected yet.`);
  });
});

document.querySelectorAll('.movie-card').forEach((card) => {
  card.addEventListener('click', (event) => {
    event.preventDefault();
    showToast(`${card.dataset.title} details are coming soon.`);
  });
});

const navItems = document.querySelectorAll('.nav-item');
let savedNav = '';
try { savedNav = sessionStorage.getItem('muvyActiveNav') || ''; } catch {}
navItems.forEach((item) => {
  if (item.dataset.nav === savedNav) {
    item.classList.add('is-active');
    if (item.tagName === 'A') item.setAttribute('aria-current', 'page');
  }
});
navItems.forEach((item) => {
  item.addEventListener('click', () => {
    try { sessionStorage.setItem('muvyActiveNav', item.dataset.nav); } catch {}
    navItems.forEach((navItem) => {
      navItem.classList.remove('is-active');
      navItem.removeAttribute('aria-current');
    });
    item.classList.add('is-active');
    if (item.tagName === 'A') item.setAttribute('aria-current', 'page');
  });
});

const searchToggle = document.getElementById('search-toggle');
const searchRow = document.getElementById('search-row');
const searchInput = document.getElementById('movie-search');
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
document.getElementById('profile-button').addEventListener('click', () => showToast('Profile settings are coming soon.'));

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

function showCaptureSession() {
  captureOptions.hidden = true;
  captureLive.hidden = false;
  capturePreview.classList.add('has-preview');
}

function showCaptureError(message) {
  captureOptions.hidden = true;
  captureLive.hidden = false;
  capturePreview.classList.remove('has-preview');
  captureStatus.textContent = message;
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
  resetCaptureDialog();
  captureDialog.showModal();
});
document.getElementById('capture-close').addEventListener('click', () => captureDialog.close());
captureDialog.addEventListener('click', (event) => {
  if (event.target === captureDialog) captureDialog.close();
});
captureDialog.addEventListener('close', resetCaptureDialog);

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
      captureStatus.textContent = 'Screen clip captured. It is ready to identify.';
    };
    captureStream.getVideoTracks()[0]?.addEventListener('ended', () => {
      if (mediaRecorder?.state === 'recording') mediaRecorder.stop();
    }, { once: true });
    recorder.start(1000);
    stopCaptureButton.textContent = 'Stop recording';
    stopCaptureButton.hidden = false;
    captureStatus.textContent = 'Recording your selected screen. Stop when you have captured the scene.';
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
    captureStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: 'environment' } },
      audio: false
    });
    showCaptureSession();
    captureVideo.srcObject = captureStream;
    await captureVideo.play();
    stopCaptureButton.textContent = 'Close camera';
    stopCaptureButton.hidden = false;
    captureFrameButton.hidden = false;
    captureStatus.textContent = 'Point the back camera at the movie, then capture a frame.';
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
  captureStatus.textContent = 'Camera closed.';
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
    captureStatus.textContent = 'Frame captured. It is ready to identify.';
  }, 'image/jpeg', .92);
});

identifyCaptureButton.addEventListener('click', () => {
  if (!captureBlob) return;
  captureStatus.textContent = 'The capture is ready, but movie identification is not connected yet.';
});
