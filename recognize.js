// MUVY Recognition
// Connects the frontend recognition UI to the deployed MUVY FastAPI backend.

const API_BASE_URL = 'https://muvy3.onrender.com';


// ---------------------------------------------------------
// Toast
// ---------------------------------------------------------

const toast = document.getElementById('recognize-toast');
let toastTimer;

function showToast(message) {
  if (!toast) return;

  toast.textContent = message;
  toast.classList.add('is-visible');

  window.clearTimeout(toastTimer);

  toastTimer = window.setTimeout(() => {
    toast.classList.remove('is-visible');
  }, 3200);
}


// ---------------------------------------------------------
// Tablet navigation
// ---------------------------------------------------------

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

  const formData = new FormData();

  formData.append('file', file, file.name || 'muvy-video.webm');

  const response = await fetch(`${API_BASE_URL}/identify`, {
    method: 'POST',
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

  const existingResult =
    document.getElementById('muvy-recognition-result');

  if (existingResult) {
    existingResult.remove();
  }

  const result = document.createElement('section');

  result.id = 'muvy-recognition-result';

  result.setAttribute('aria-live', 'polite');

  const posterUrl = getPosterUrl(movie.poster_path);

  const confidence =
    typeof match.confidence === 'number'
      ? `${Math.round(match.confidence * 100)}%`
      : '—';

  const timestamp =
    typeof match.timestamp_seconds === 'number'
      ? `${match.timestamp_seconds.toFixed(2)}s`
      : '—';

  result.innerHTML = `
    <div class="muvy-result-card">

      ${
        posterUrl
          ? `
            <div class="muvy-result-poster">
              <img
                src="${posterUrl}"
                alt="${escapeHtml(movie.title || 'Movie poster')}"
                loading="lazy"
              />
            </div>
          `
          : ''
      }

      <div class="muvy-result-info">

        <p class="muvy-result-label">
          Movie identified
        </p>

        <h2>
          ${escapeHtml(movie.title || 'Unknown movie')}
        </h2>

        ${
          movie.runtime
            ? `<p>${movie.runtime} min</p>`
            : ''
        }

        ${
          movie.release_date
            ? `<p>${escapeHtml(movie.release_date)}</p>`
            : ''
        }

        ${
          movie.overview
            ? `
              <p class="muvy-result-overview">
                ${escapeHtml(movie.overview)}
              </p>
            `
            : ''
        }

        <div class="muvy-result-stats">

          <div>
            <span>Confidence</span>
            <strong>${confidence}</strong>
          </div>

          <div>
            <span>Matched at</span>
            <strong>${timestamp}</strong>
          </div>

          ${
            typeof match.votes === 'number'
              ? `
                <div>
                  <span>Votes</span>
                  <strong>${match.votes}</strong>
                </div>
              `
              : ''
          }

        </div>

      </div>

    </div>
  `;

  const recognitionArea =
    document.querySelector('main') ||
    document.body;

  recognitionArea.appendChild(result);

  result.scrollIntoView({
    behavior: 'smooth',
    block: 'center',
  });
}


// ---------------------------------------------------------
// HTML escaping
// ---------------------------------------------------------

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}


// ---------------------------------------------------------
// Upload video
// ---------------------------------------------------------

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
    audioButtonLabel.textContent = isListening
      ? 'Stop audio recognition'
      : 'Start audio recognition';
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
        'Audio recording is not supported in this browser.';
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
          'Audio captured. Audio recognition will be connected when the MUVY audio fingerprint service is available.';
      }
    };

    if (audioFeedback) {
      audioFeedback.hidden = false;
    }

    if (audioStatus) {
      audioStatus.textContent =
        'Listening for up to 10 seconds. Play the movie audio now.';
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
        error.name === 'NotAllowedError'
          ? 'Microphone permission was not granted.'
          : 'Could not access the microphone.';
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

const captureDialog =
  document.getElementById('capture-dialog');

const captureOptions =
  document.getElementById('capture-options');

const captureLive =
  document.getElementById('capture-live');

const captureVideo =
  document.getElementById('capture-video');

const capturePreview =
  document.querySelector('.capture-preview');

const captureStatus =
  document.getElementById('capture-status');

const stopCaptureButton =
  document.getElementById('stop-capture');

const captureFrameButton =
  document.getElementById('capture-frame');

const identifyCaptureButton =
  document.getElementById('identify-capture');

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
    captureStatus.textContent = message;
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


const captureClose =
  document.getElementById('capture-close');

if (captureClose && captureDialog) {
  captureClose.addEventListener(
    'click',
    () => captureDialog.close()
  );
}


if (captureDialog) {
  captureDialog.addEventListener(
    'click',
    (event) => {
      if (event.target === captureDialog) {
        captureDialog.close();
      }
    }
  );

  captureDialog.addEventListener(
    'close',
    resetCaptureDialog
  );
}


// ---------------------------------------------------------
// Screen recording
// ---------------------------------------------------------

const screenRecordOption =
  document.getElementById(
    'screen-record-option'
  );

if (screenRecordOption) {
  screenRecordOption.addEventListener(
    'click',
    async () => {

      if (
        !navigator.mediaDevices?.getDisplayMedia ||
        !window.MediaRecorder
      ) {
        showCaptureError(
          'Screen recording is not supported here. You can upload a clip instead.'
        );

        return;
      }

      try {
        captureStream =
          await navigator.mediaDevices.getDisplayMedia({
            video: true,
            audio: false,
          });

        showCaptureSession();

        captureVideo.srcObject =
          captureStream;

        await captureVideo
          .play()
          .catch(() => {});

        recordedChunks = [];
        captureBlob = null;

        const mimeType = [
          'video/webm;codecs=vp9',
          'video/webm;codecs=vp8',
          'video/webm',
        ].find((type) =>
          MediaRecorder.isTypeSupported(type)
        );

        const recorder =
          new MediaRecorder(
            captureStream,
            mimeType
              ? { mimeType }
              : undefined
          );

        mediaRecorder = recorder;

        recorder.ondataavailable = (
          event
        ) => {
          if (event.data.size) {
            recordedChunks.push(
              event.data
            );
          }
        };

        recorder.onstop = async () => {
          if (mediaRecorder !== recorder) {
            return;
          }

          captureBlob = new Blob(
            recordedChunks,
            {
              type:
                recorder.mimeType ||
                'video/webm',
            }
          );

          stopCaptureStream();

          if (stopCaptureButton) {
            stopCaptureButton.hidden = true;
          }

          if (identifyCaptureButton) {
            identifyCaptureButton.hidden = false;
          }

          if (captureStatus) {
            captureStatus.textContent =
              'Screen clip captured. Ready to identify.';
          }
        };

        captureStream
          .getVideoTracks()[0]
          ?.addEventListener(
            'ended',
            () => {
              if (
                recorder.state ===
                'recording'
              ) {
                recorder.stop();
              }
            },
            { once: true }
          );

        recorder.start(1000);

        if (stopCaptureButton) {
          stopCaptureButton
            .querySelector('span')
            ?.replaceChildren(
              document.createTextNode(
                'Stop recording'
              )
            );

          stopCaptureButton.hidden = false;
        }

        if (captureStatus) {
          captureStatus.textContent =
            'Recording your selected screen. Stop after 10 to 15 seconds.';
        }

        captureTimer =
          window.setTimeout(() => {
            if (
              recorder.state ===
              'recording'
            ) {
              recorder.stop();
            }
          }, 15000);

      } catch (error) {
        stopCaptureStream();

        showCaptureError(
          error.name === 'NotAllowedError'
            ? 'Screen capture was cancelled. Choose an option to try again.'
            : 'Could not start screen capture. Choose an option to try again.'
        );
      }
    }
  );
}


// ---------------------------------------------------------
// Back camera
// ---------------------------------------------------------

const backCameraOption =
  document.getElementById(
    'back-camera-option'
  );

if (backCameraOption) {
  backCameraOption.addEventListener(
    'click',
    async () => {

      if (!navigator.mediaDevices?.getUserMedia) {
        showCaptureError(
          'Camera access is not available in this browser.'
        );

        return;
      }

      try {
        captureStream =
          await navigator.mediaDevices.getUserMedia({
            video: {
              facingMode: {
                ideal: 'environment',
              },
            },
            audio: false,
          });

        showCaptureSession();

        captureVideo.srcObject =
          captureStream;

        await captureVideo.play();

        if (stopCaptureButton) {
          stopCaptureButton
            .querySelector('span')
            ?.replaceChildren(
              document.createTextNode(
                'Close camera'
              )
            );

          stopCaptureButton.hidden = false;
        }

        if (captureFrameButton) {
          captureFrameButton.hidden = false;
        }

        if (captureStatus) {
          captureStatus.textContent =
            'Point the back camera at the movie, then capture a frame.';
        }

      } catch (error) {
        stopCaptureStream();

        showCaptureError(
          error.name === 'NotAllowedError'
            ? 'Camera permission was not granted. Choose an option to try again.'
            : 'Could not open the back camera. Choose an option to try again.'
        );
      }
    }
  );
}


// ---------------------------------------------------------
// Stop capture
// ---------------------------------------------------------

if (stopCaptureButton) {
  stopCaptureButton.addEventListener(
    'click',
    () => {

      window.clearTimeout(
        captureTimer
      );

      if (
        mediaRecorder?.state ===
        'recording'
      ) {
        mediaRecorder.stop();
        return;
      }

      stopCaptureStream();

      stopCaptureButton.hidden = true;

      if (captureFrameButton) {
        captureFrameButton.hidden = true;
      }

      if (captureStatus) {
        captureStatus.textContent =
          'Camera closed.';
      }
    }
  );
}


// ---------------------------------------------------------
// Camera frame
// ---------------------------------------------------------

if (captureFrameButton) {
  captureFrameButton.addEventListener(
    'click',
    () => {

      if (
        !captureVideo.videoWidth ||
        !captureVideo.videoHeight
      ) {
        return;
      }

      const canvas =
        document.createElement(
          'canvas'
        );

      canvas.width =
        captureVideo.videoWidth;

      canvas.height =
        captureVideo.videoHeight;

      const context =
        canvas.getContext('2d');

      if (!context) {
        return;
      }

      context.drawImage(
        captureVideo,
        0,
        0
      );

      canvas.toBlob(
        (blob) => {

          captureBlob = blob;

          stopCaptureStream();

          if (stopCaptureButton) {
            stopCaptureButton.hidden = true;
          }

          captureFrameButton.hidden = true;

          if (identifyCaptureButton) {
            identifyCaptureButton.hidden = false;
          }

          if (captureStatus) {
            captureStatus.textContent =
              'Frame captured. Camera-image recognition will be connected in a later backend update.';
          }
        },
        'image/jpeg',
        0.92
      );
    }
  );
}


// ---------------------------------------------------------
// Identify screen recording / capture
// ---------------------------------------------------------

if (identifyCaptureButton) {
  identifyCaptureButton.addEventListener(
    'click',
    async () => {

      if (!captureBlob) {
        if (captureStatus) {
          captureStatus.textContent =
            'There is no capture to identify.';
        }

        return;
      }

      /*
       * The current backend /identify endpoint
       * accepts video files.
       *
       * Screen recordings are video, so send them
       * directly to the MUVY API.
       *
       * Camera captures are JPEG images and therefore
       * are intentionally not sent to /identify yet.
       */

      const isVideo =
        captureBlob.type.startsWith(
          'video/'
        );

      if (!isVideo) {
        if (captureStatus) {
          captureStatus.textContent =
            'This camera capture is an image. Camera-image recognition will be added when the backend supports image fingerprints.';
        }

        return;
      }

      if (captureStatus) {
        captureStatus.textContent =
          'Identifying movie... This may take a little while.';
      }

      identifyCaptureButton.disabled = true;

      try {

        const file = new File(
          [captureBlob],
          'muvy-screen-recording.webm',
          {
            type:
              captureBlob.type ||
              'video/webm',
          }
        );

        const data =
          await identifyVideoFile(
            file
          );

        displayRecognitionResult(
          data
        );

        if (
          data.matched &&
          data.movie
        ) {
          showToast(
            `Identified: ${data.movie.title}`
          );

          if (captureStatus) {
            captureStatus.textContent =
              `Identified: ${data.movie.title}`;
          }
        } else {
          if (captureStatus) {
            captureStatus.textContent =
              data.message ||
              'No confident movie match found.';
          }
        }

      } catch (error) {

        console.error(
          'MUVY screen identification error:',
          error
        );

        if (captureStatus) {
          captureStatus.textContent =
            error.message ||
            'Movie identification failed.';
        }

        showToast(
          error.message ||
          'Movie identification failed.'
        );

      } finally {
        identifyCaptureButton.disabled =
          false;
      }
    }
  );
}
