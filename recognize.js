// Recognition interactions: audio, timed screen capture, camera frames, and file selection.
const toast = document.getElementById('recognize-toast');
let toastTimer;
function showToast(message) {
  toast.textContent = message;
  toast.classList.add('is-visible');
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove('is-visible'), 3200);
}

// Tablet navigation menu and preview actions.
const menuToggle = document.getElementById('recognize-menu-toggle');
const menuPanel = document.getElementById('recognize-menu-panel');
menuToggle.addEventListener('click', () => {
  const willOpen = menuPanel.hidden;
  menuPanel.hidden = !willOpen;
  menuToggle.setAttribute('aria-expanded', String(willOpen));
});
document.addEventListener('click', (event) => {
  if (!menuPanel.hidden && !menuPanel.contains(event.target) && !menuToggle.contains(event.target)) {
    menuPanel.hidden = true;
    menuToggle.setAttribute('aria-expanded', 'false');
  }
});
document.querySelectorAll('[data-message]').forEach((button) => {
  button.addEventListener('click', () => showToast(button.dataset.message));
});

const clipPicker = document.getElementById('clip-picker');
document.getElementById('upload-choice').addEventListener('click', () => clipPicker.click());
clipPicker.addEventListener('change', () => {
  const file = clipPicker.files && clipPicker.files[0];
  if (file) showToast(`${file.name} selected. Movie recognition is not connected yet.`);
});

const audioFeedback = document.getElementById('audio-feedback');
const audioStatus = document.getElementById('audio-status');
const stopAudioButton = document.getElementById('stop-audio');
const audioRecognitionButton = document.getElementById('audio-recognition-button');
const audioButtonLabel = document.getElementById('audio-button-label');
const audioButtonEqIcon = audioRecognitionButton.querySelector('.audio-button-eq');
const audioButtonStopIcon = audioRecognitionButton.querySelector('.audio-button-stop');
let audioStream = null;
let audioRecorder = null;
let audioTimer = null;
let audioChunks = [];

function setAudioButtonListening(isListening) {
  audioRecognitionButton.classList.toggle('is-listening', isListening);
  audioRecognitionButton.setAttribute('aria-pressed', String(isListening));
  audioButtonEqIcon.hidden = isListening;
  audioButtonStopIcon.hidden = !isListening;
  audioButtonLabel.textContent = isListening ? 'Stop audio recognition' : 'Start audio recognition';
}

function stopAudioCapture() {
  window.clearTimeout(audioTimer);
  if (audioRecorder && audioRecorder.state === 'recording') audioRecorder.stop();
  if (audioStream) audioStream.getTracks().forEach((track) => track.stop());
  audioStream = null;
  stopAudioButton.hidden = true;
  setAudioButtonListening(false);
}

const startAudioRecognition = async () => {
  if (audioRecorder?.state === 'recording') {
    stopAudioCapture();
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    audioFeedback.hidden = false;
    audioStatus.textContent = 'Audio recording is not supported in this browser.';
    return;
  }
  try {
    audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];
    audioRecorder = new MediaRecorder(audioStream);
    audioRecorder.ondataavailable = (event) => { if (event.data.size) audioChunks.push(event.data); };
    audioRecorder.onstop = () => {
      if (audioStream) audioStream.getTracks().forEach((track) => track.stop());
      audioStream = null;
      stopAudioButton.hidden = true;
      setAudioButtonListening(false);
      audioStatus.textContent = 'Audio captured. Movie identification is not connected yet.';
    };
    audioFeedback.hidden = false;
    audioStatus.textContent = 'Listening for up to 10 seconds. Play the movie audio now.';
    stopAudioButton.hidden = false;
    audioRecorder.start();
    setAudioButtonListening(true);
    audioTimer = window.setTimeout(stopAudioCapture, 10000);
  } catch (error) {
    audioFeedback.hidden = false;
    audioStatus.textContent = error.name === 'NotAllowedError'
      ? 'Microphone permission was not granted.'
      : 'Could not access the microphone.';
  }
};
document.getElementById('audio-choice').addEventListener('click', startAudioRecognition);
audioRecognitionButton.addEventListener('click', () => {
  if (audioRecorder?.state === 'recording') stopAudioCapture();
  else startAudioRecognition();
});
stopAudioButton.addEventListener('click', stopAudioCapture);

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
  captureOptions.hidden = true;
  captureLive.hidden = false;
  capturePreview.classList.remove('has-preview');
  captureStatus.textContent = message;
  stopCaptureButton.hidden = true;
  captureFrameButton.hidden = true;
  identifyCaptureButton.hidden = true;
}
function showCaptureSession() {
  captureOptions.hidden = true;
  captureLive.hidden = false;
  capturePreview.classList.add('has-preview');
}
function stopCaptureStream() {
  if (captureStream) captureStream.getTracks().forEach((track) => track.stop());
  captureStream = null;
  captureVideo.srcObject = null;
  capturePreview.classList.remove('has-preview');
}
function resetCaptureDialog() {
  window.clearTimeout(captureTimer);
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

document.getElementById('screen-choice').addEventListener('click', () => {
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
      captureStatus.textContent = 'Screen clip captured. Movie identification is not connected yet.';
    };
    captureStream.getVideoTracks()[0]?.addEventListener('ended', () => {
      if (recorder.state === 'recording') recorder.stop();
    }, { once: true });
    recorder.start(1000);
    stopCaptureButton.querySelector('span').textContent = 'Stop recording';
    stopCaptureButton.hidden = false;
    captureStatus.textContent = 'Recording your selected screen. Stop after 10 to 15 seconds.';
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
  if (!navigator.mediaDevices?.getUserMedia) {
    showCaptureError('Camera access is not available in this browser.');
    return;
  }
  try {
    captureStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false });
    showCaptureSession();
    captureVideo.srcObject = captureStream;
    await captureVideo.play();
    stopCaptureButton.querySelector('span').textContent = 'Close camera';
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
  window.clearTimeout(captureTimer);
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
    captureStatus.textContent = 'Frame captured. Movie identification is not connected yet.';
  }, 'image/jpeg', .92);
});
identifyCaptureButton.addEventListener('click', () => {
  if (captureBlob) captureStatus.textContent = 'Your capture is ready. Connect the MUVY identification service to identify it.';
});
