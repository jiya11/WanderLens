// DOM Elements for camera and scanning functionality
const video = document.getElementById("video");        // Live camera feed element
const canvas = document.getElementById("canvas");      // Hidden canvas for image capture
const scanBtn = document.getElementById("scanBtn");    // Button to trigger landmark scanning

// DOM Elements for overlay display (shows landmark information)
const overlay = document.getElementById("overlay");           // Container for landmark info overlay
const overlayTitle = document.getElementById("overlayTitle"); // Landmark name display
const overlayText = document.getElementById("overlayText");   // Landmark description display
const saveBtn = document.getElementById("saveBtn");          // Button to save to passport
const closeOverlayBtn = document.getElementById("closeOverlayBtn"); // Button to close overlay

// DOM Elements for attractions and food spots functionality
const findAttractionsBtn = document.getElementById("findAttractionsBtn");    // Button to find nearby places
const attractionsPopup = document.getElementById("attractionsPopup");        // Popup container for places
const attractionsList = document.getElementById("attractionsList");          // List of nearby attractions
const closeAttractionsBtn = document.getElementById("closeAttractionsBtn");  // Close popup button
const attractionsTab = document.getElementById("attractionsTab");            // Tab for attractions view

// DOM Elements for food spots tab
const foodTab = document.getElementById("foodTab");    // Tab for food spots view
const foodList = document.getElementById("foodList");  // List of nearby food spots

const BACKEND_URL = "http://127.0.0.1:5001";

/*
 * Gesture Recognition Implementation
 * --------------------------------
 * This implementation uses MediaPipe Gesture Recognizer
 * Original code adapted from:
 * - Google MediaPipe Tasks: https://developers.google.com/mediapipe/solutions/vision/gesture_recognizer
 * - Official Demo: https://codepen.io/mediapipe-preview/pen/zYamdVd
 * - License: Apache 2.0 (https://github.com/google/mediapipe/blob/master/LICENSE)
 * 
 * Modifications:
 * - Integrated with WanderLens camera system
 * - Added custom gesture handlers for app-specific actions
 * - Added debouncing and confidence thresholds
 * - Added error handling and recovery
 */

// Gesture recognition state
let gestureRecognizer = null;
let lastGesture = null;
let gestureTimeout = null;
// Countdown state for gesture-triggered scan (peace sign)
let countdownInProgress = false;
let countdownTimer = null;
let countdownElement = null;

// Initialize gesture recognizer
async function initGestureRecognition() {
  try {
    const { GestureRecognizer, FilesetResolver } = window.gestureModule;
    
    const vision = await FilesetResolver.forVisionTasks(
      "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm"
    );

    gestureRecognizer = await GestureRecognizer.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath:
          "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/latest/gesture_recognizer.task",
      },
      runningMode: "VIDEO",
      numHands: 1,
    });
    
    console.log("Gesture recognizer initialized");
    return true;
  } catch (error) {
    console.error("Error initializing gesture recognizer:", error);
    return false;
  }
}

// Handle gestures
function handleGesture(gestureName) {
  if (lastGesture === gestureName) return; // Prevent duplicate triggers
  lastGesture = gestureName;
  
  if (gestureTimeout) clearTimeout(gestureTimeout);
  gestureTimeout = setTimeout(() => lastGesture = null, 1000); // Reset after 1 second
  
  console.log("Gesture detected:", gestureName);
  
  switch (gestureName) {
    case "Thumb_Up":
      if (!overlay.classList.contains('hidden')) {
        saveBtn.click();
      }
      break;
    case "Thumb_Down":
      // If a countdown is running, Thumb_Down acts as a cancel
      if (countdownInProgress) {
        cancelGestureCountdown();
        return;
      }

      if (!overlay.classList.contains('hidden')) {
        closeOverlayBtn.click();
      } else if (!attractionsPopup.classList.contains('hidden')) {
        closeAttractionsBtn.click();
      }
      break;
    case "Victory":
      // On peace/victory sign: start a 3-second countdown before scanning
      if (!countdownInProgress) {
        startGestureCountdown(3, () => {
          // Trigger the same action as clicking the Scan button after countdown
          scanBtn.click();
        });
      }
      break;
    case "Open_Palm":
      findAttractionsBtn.click();
      break;
    case "Pointing_Up":
      if (!attractionsPopup.classList.contains('hidden')) {
        attractionsTab.click();
      }
      break;
    case "ILoveYou":
      if (!attractionsPopup.classList.contains('hidden')) {
        foodTab.click();
      }
      break;
  }
}

// Process video frame for gestures
async function detectGestures() {
  if (!gestureRecognizer || video.paused || video.ended) return;
  
  try {
    const startTimeMs = performance.now();
    const results = gestureRecognizer.recognizeForVideo(video, startTimeMs);
    
    if (results.gestures?.length > 0) {
      const gesture = results.gestures[0][0];
      if (gesture.score > 0.7) { // Only handle confident gestures
        handleGesture(gesture.categoryName);
      }
    }
  } catch (error) {
    console.error("Error detecting gestures:", error);
  }
  
  requestAnimationFrame(detectGestures);
}

/**
 * Create and start a visual countdown overlay for gesture-triggered actions
 * @param {number} seconds - number of seconds to count down
 * @param {Function} onComplete - called when countdown reaches zero
 */
function startGestureCountdown(seconds, onComplete) {
  countdownInProgress = true;

  // Create a simple countdown element centered over the video frame
  countdownElement = document.createElement('div');
  countdownElement.id = 'gesture-countdown';
  countdownElement.style.position = 'absolute';
  countdownElement.style.top = '50%';
  countdownElement.style.left = '50%';
  countdownElement.style.transform = 'translate(-50%, -50%)';
  countdownElement.style.zIndex = 9999;
  countdownElement.style.background = 'rgba(0,0,0,0.6)';
  countdownElement.style.color = '#fff';
  countdownElement.style.fontSize = '56px';
  countdownElement.style.padding = '18px 28px';
  countdownElement.style.borderRadius = '14px';
  countdownElement.style.fontWeight = '700';
  countdownElement.style.textAlign = 'center';
  countdownElement.style.boxShadow = '0 8px 24px rgba(0,0,0,0.6)';
  countdownElement.style.pointerEvents = 'none';

  // Insert into the same container as the video so it overlays correctly
  const videoFrame = document.querySelector('.video-frame') || document.body;
  // Ensure the container is positioned so absolute child centers correctly
  if (videoFrame && getComputedStyle(videoFrame).position === 'static') {
    videoFrame.style.position = 'relative';
  }
  videoFrame.appendChild(countdownElement);

  // Show initial value
  let remaining = Math.max(1, Math.floor(seconds));
  countdownElement.textContent = remaining;

  // Update every second
  countdownTimer = setInterval(() => {
    remaining -= 1;
    if (remaining > 0) {
      countdownElement.textContent = remaining;
    } else {
      // End countdown
      clearInterval(countdownTimer);
      countdownTimer = null;
      removeCountdownElement();
      // Small delay to allow UI to update then call onComplete
      try { if (typeof onComplete === 'function') onComplete(); } catch (e) { console.error('Countdown onComplete error', e); }
      countdownInProgress = false;
    }
  }, 1000);
}

/**
 * Cancel an active gesture countdown (if any) and remove UI
 */
function cancelGestureCountdown() {
  if (!countdownInProgress) return;
  if (countdownTimer) {
    clearInterval(countdownTimer);
    countdownTimer = null;
  }
  removeCountdownElement();
  countdownInProgress = false;
  console.log('Gesture countdown cancelled');
}

function removeCountdownElement() {
  if (countdownElement && countdownElement.parentNode) {
    countdownElement.parentNode.removeChild(countdownElement);
    countdownElement = null;
  }
}

/**
 * Initializes and starts the device camera
 * - Requests camera access with environment-facing preference
 * - Sets up video stream
 * - Initializes gesture recognition after video loads
 * - Handles permission errors and device access issues
 */
async function startCamera() {
  try {
    // Request camera access, preferring rear-facing camera if available
    const stream = await navigator.mediaDevices.getUserMedia({ 
      video: { facingMode: "environment" }, // Use rear camera if available
      audio: false // No audio needed
    });
    video.srcObject = stream;
    
    // Initialize gesture recognition once video is ready
    video.addEventListener('loadeddata', async () => {
      const gestureInitialized = await initGestureRecognition();
      if (gestureInitialized) {
        detectGestures();
        console.log("Gesture detection started");
      }
    });
  } catch (err) {
    console.error("Camera error:", err);
    alert("Unable to access camera. Please allow camera permissions.");
  }
}

/**
 * Captures the current frame from the video feed
 * - Maintains aspect ratio of the video feed
 * - Uses fallback dimensions if video size is not available
 * - Returns a base64 encoded PNG image
 * @returns {string} Base64 encoded PNG image data URL
 */
function captureFrame() {
  // Get dimensions, fallback to standard mobile dimensions if not available
  const w = video.videoWidth || 720;   // Default width if not available
  const h = video.videoHeight || 1280;  // Default height if not available
  
  // Set canvas dimensions to match video
  canvas.width = w;
  canvas.height = h;
  
  // Draw the current video frame to the canvas
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, w, h);
  
  // Convert to base64 PNG
  return canvas.toDataURL("image/png");
}

/**
 * Displays the landmark information overlay
 * @param {string} name - The name of the landmark
 * @param {string} info - Description or additional information
 */
function showOverlay(name, info) {
  overlayTitle.textContent = name || "Unknown";              // Set landmark name with fallback
  overlayText.textContent = info || "No description available."; // Set info with fallback
  overlay.classList.remove("hidden");                        // Make overlay visible
}

/**
 * Hides the landmark information overlay
 */
function hideOverlay() {
  overlay.classList.add("hidden");
}

/**
 * Saves a landmark entry to the user's digital passport
 * - Stores in browser's localStorage
 * - Prevents duplicate entries
 * - Adds new entries to the beginning of the list
 * 
 * @param {Object} entry - The landmark entry to save
 * @param {string} entry.id - Unique identifier
 * @param {string} entry.name - Landmark name
 * @param {string} entry.info - Description
 * @returns {boolean} True if saved successfully, false if entry already exists
 */
function saveToPassport(entry) {
  const key = "passportEntries";
  const existing = JSON.parse(localStorage.getItem(key) || "[]");
  
  // Check if entry already exists (by id or name)
  const existingIndex = existing.findIndex(e => e.id === entry.id || e.name === entry.name);
  if (existingIndex !== -1) {
    return false; // Already exists
  }
  
  // Add the new entry at the start of the array
  existing.unshift(entry);
  localStorage.setItem(key, JSON.stringify(existing));
  return true;
}

/**
 * Sends an image to the backend for landmark recognition
 * - Converts image to base64 format
 * - Makes POST request to analysis endpoint
 * - Handles response and errors
 * 
 * @param {string} imageDataUrl - Base64 encoded image data
 * @returns {Promise<Object>} Analyzed landmark data
 * @throws {Error} If analysis request fails
 */
async function analyzeImage(imageDataUrl) {
  const res = await fetch(`${BACKEND_URL}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image: imageDataUrl })
  });
  if (!res.ok) {
    // Try to read JSON error from the server to make debugging easier
    let bodyText = await res.text();
    try {
      const bodyJson = JSON.parse(bodyText || "{}");
      const msg = bodyJson.message || bodyJson.error || bodyJson.error_description || bodyText;
      throw new Error(`Analyze failed: ${res.status} - ${msg}`);
    } catch (e) {
      throw new Error(`Analyze failed: ${res.status} - ${bodyText}`);
    }
  }
  return res.json();
}

// Location caching system
// Stores the last known good location to reduce API calls and provide fallback
let lastKnownLocation = null;          // Cache of the last valid location
let lastLocationTime = 0;              // Timestamp of when location was last updated
const LOCATION_CACHE_DURATION = 5 * 60 * 1000; // Cache duration (5 minutes)

/**
 * Opens Google Maps directions to a specified place
 * - Uses place name instead of coordinates for better accuracy
 * - Opens in a new tab
 * - Automatically uses user's current location as starting point
 * 
 * @param {string} placeName - Name of the destination place
 */
function openDirectionsToName(placeName) {
  // URL encode the place name to handle special characters
  const encoded = encodeURIComponent(placeName);
  
  // Open Google Maps in a new tab with directions
  // Note: Google Maps will automatically use user's current location as start point
  window.open(`https://www.google.com/maps/dir/?api=1&destination=${encoded}`, "_blank");
}

/**
 * Gets the user's current location with advanced fallback strategies
 * - Tries cached location first to avoid unnecessary API calls
 * - Uses high accuracy mode with reasonable timeout
 * - Falls back to watching position if initial request fails
 * - Implements comprehensive error handling
 * - Caches successful locations for future use
 * 
 * @returns {Promise<Object>} Object containing lat and lon coordinates
 * @throws {Error} If location cannot be determined
 */
async function getCurrentLocation() {
  return new Promise((resolve, reject) => {
    // First check if we have a valid cached location
    const now = Date.now();
    if (lastKnownLocation && (now - lastLocationTime) < LOCATION_CACHE_DURATION) {
      console.log('Using cached location');
      return resolve(lastKnownLocation);
    }

    if (!navigator.geolocation) {
      reject(new Error('Geolocation is not supported by this browser.'));
      return;
    }

    // Function to handle successful position
    const handleSuccess = (position) => {
      const location = {
        lat: position.coords.latitude,
        lon: position.coords.longitude
      };
      
      // Cache the successful location
      lastKnownLocation = location;
      lastLocationTime = Date.now();
      
      if (watchId) navigator.geolocation.clearWatch(watchId);
      if (timeoutId) clearTimeout(timeoutId);
      resolve(location);
    };

    // Function to handle errors
    const handleError = (error) => {
      let errorMessage = 'Unable to get your location. ';
      switch (error.code) {
        case 1:
          errorMessage += 'Please enable location access in your browser settings.';
          break;
        case 2:
          errorMessage += 'Position unavailable. Please check your device\'s location settings.';
          break;
        case 3:
          errorMessage += 'Request timed out. Please try again.';
          break;
        default:
          errorMessage += error.message;
      }
      console.error('Geolocation error:', error);
      
      // If we have a cached location, use it as fallback
      if (lastKnownLocation) {
        console.log('Falling back to cached location');
        resolve(lastKnownLocation);
      } else {
        reject(new Error(errorMessage));
      }
    };

    // Try high accuracy first
    const options = {
      enableHighAccuracy: true,
      timeout: 5000,
      maximumAge: 0
    };

    let watchId = null;
    let timeoutId = null;
    let hasResolved = false;

    // Start with getCurrentPosition for a quick result
    navigator.geolocation.getCurrentPosition(
      handleSuccess,
      () => {
        // If getCurrentPosition fails, try watchPosition
        console.log('getCurrentPosition failed, trying watchPosition...');
        watchId = navigator.geolocation.watchPosition(
          handleSuccess,
          (error) => {
            // Only handle error if we haven't succeeded yet
            if (!hasResolved) {
              hasResolved = true;
              handleError(error);
            }
          },
          options
        );

        // Set a timeout for the watch
        timeoutId = setTimeout(() => {
          if (watchId) {
            navigator.geolocation.clearWatch(watchId);
            if (!hasResolved) {
              hasResolved = true;
              handleError({ code: 3, message: 'Location request timed out.' });
            }
          }
        }, 15000); // 15 second total timeout
      },
      options
    );
  });
}

/**
 * Fetches nearby attractions from the backend
 * - Uses OpenStreetMap data through backend API
 * - Supports configurable search radius
 * - Includes distance and walking time calculations
 * 
 * @param {number} lat - Latitude of current location
 * @param {number} lon - Longitude of current location
 * @param {number} [radius=1000] - Search radius in meters (default 1km)
 * @returns {Promise<Object>} Attractions data including distances
 * @throws {Error} If backend request fails
 */
async function fetchAttractions(lat, lon, radius = 1000) {
  try {
    const response = await fetch(`${BACKEND_URL}/attractions?lat=${lat}&lon=${lon}&radius=${radius}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error('Error fetching attractions:', error);
    throw error;
  }
}

/**
 * Fetches nearby food spots from the backend
 * - Similar to fetchAttractions but for restaurants/cafes
 * - Uses same location and radius parameters
 * - Includes distance and estimated travel time
 * 
 * @param {number} lat - Latitude of current location
 * @param {number} lon - Longitude of current location
 * @param {number} [radius=1000] - Search radius in meters (default 1km)
 * @returns {Promise<Object>} Food spots data including distances
 * @throws {Error} If backend request fails
 */
async function fetchFoodSpots(lat, lon, radius = 1000) {
  try {
    const response = await fetch(`${BACKEND_URL}/food?lat=${lat}&lon=${lon}&radius=${radius}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error('Error fetching food spots:', error);
    throw error;
  }
}

/**
 * Checks if a place is already saved in the user's passport
 * - Searches by both ID and name to handle different data sources
 * - Uses localStorage for persistent storage
 * 
 * @param {string} placeId - Unique identifier for the place
 * @param {string} placeName - Name of the place (fallback identifier)
 * @returns {Object} Object containing saved status and stored ID
 */
function getSavedPlaceInfo(placeId, placeName) {
  const entries = JSON.parse(localStorage.getItem('passportEntries') || '[]');
  const entry = entries.find(entry => entry.id === placeId || entry.name === placeName);
  return entry ? { isSaved: true, storedId: entry.id } : { isSaved: false, storedId: null };
}

/**
 * Removes a place from the user's passport
 * - Finds entry by stored ID
 * - Updates localStorage after removal
 * 
 * @param {string} storedId - ID of the saved entry to remove
 * @returns {boolean} True if successfully removed, false if not found
 */
function removeFromPassport(storedId) {
  const entries = JSON.parse(localStorage.getItem('passportEntries') || '[]');
  const index = entries.findIndex(entry => entry.id === storedId);
  if (index !== -1) {
    entries.splice(index, 1);
    localStorage.setItem('passportEntries', JSON.stringify(entries));
    return true;
  }
  return false;
}

/**
 * Handles toggling a place's saved status in the passport
 * - Updates UI to reflect current saved state
 * - Manages save/remove operations
 * - Updates button appearance and text
 * 
 * @param {HTMLElement} button - The button element that triggered the toggle
 * @param {Object} entry - The place entry to toggle
 */
function handlePassportToggle(button, entry) {
  const card = button.closest('.attraction-card');
  const { isSaved, storedId } = getSavedPlaceInfo(entry.id, entry.name);
  
  if (isSaved) {
    if (removeFromPassport(storedId)) {
      card.classList.remove('saved');
      button.textContent = 'Add to Passport';
      button.classList.remove('btn-danger');
      button.classList.add('btn-primary');
    }
  } else {
    saveToPassport(entry);
    card.classList.add('saved');
    button.textContent = 'Remove from Passport';
    button.classList.remove('btn-primary');
    button.classList.add('btn-danger');
  }
}

/**
 * Renders a list of places (attractions or food spots) in the UI
 * - Handles both attraction and food spot displays
 * - Checks saved status for each place
 * - Creates interactive cards with save/remove functionality
 * - Shows empty state message if no places found
 * 
 * @param {Object} data - The places data to display
 * @param {string} type - Type of places ('attraction' or 'food')
 */
function displayPlaces(data, type = 'attraction') {
  // Determine which container and data to use based on type
  const container = type === 'attraction' ? attractionsList : foodList;
  const places = type === 'attraction' ? data.attractions : data.food_spots;
  const count = type === 'attraction' ? data.count : data.food_count;
  
  if (!places || count === 0) {
    // Show empty state message if no places found
    container.innerHTML = `<p class="no-attractions">No ${type}s found nearby. Try increasing the search radius.</p>`;
  } else {
    // Generate HTML for each place
    container.innerHTML = places.map(place => {
      const { isSaved } = getSavedPlaceInfo(place.id, place.name);
      const buttonText = isSaved ? 'Remove from Passport' : 'Add to Passport';
      const buttonClass = isSaved ? 'btn-danger' : 'btn-primary';
      const hasCoords = typeof place.lat === 'number' && typeof place.lon === 'number' && !isNaN(place.lat) && !isNaN(place.lon);
      // Build the entry object for passport
      const entryObj = {
        id: Date.now().toString(),
        name: place.name,
        info: place.description || '',
        type: type,
        distance_km: place.distance_km,
        timestamp: new Date().toISOString(),
        toDiscover: true,
        image: null
      };
      // Safely encode entryObj for inline JS
      const entryObjStr = encodeURIComponent(JSON.stringify(entryObj));
      return [
        `<div class="attraction-card ${isSaved ? 'saved' : ''}" data-type="${type}" data-id="${place.id}">`,
        '  <div class="attraction-header">',
        `    <h4>${place.name}</h4>`,
        '    <div class="attraction-distance">',
        `      <span class="distance">${place.distance_km} km</span>`,
        `      <span class="walking-time">${place.walking_time_min} min walk</span>`,
        '    </div>',
        '  </div>',
        `  <p class="attraction-type">${place.type || (type === 'food' ? 'Restaurant' : 'Attraction')}</p>`,
        place.description ? `<p class="attraction-description">${place.description}</p>` : '',
        place.opening_hours ? `<p class="attraction-hours">Hours: ${place.opening_hours}</p>` : '',
        place.website ? `<a href="${place.website}" target="_blank" class="attraction-website">Visit Website</a>` : '',
        `<button class="btn ${buttonClass} save-to-passport" onclick="handlePassportToggle(this, JSON.parse(decodeURIComponent('${entryObjStr}')))">${buttonText}</button>`,
  (place.name ? `<button class="btn btn-secondary directions-btn" onclick="openDirectionsToName('${place.name.replace(/'/g, "\\'")}')">Get Directions</button>` : ''),
        '</div>'
      ].join('\n');
    }).join('');
    // (removed broken leftover code)
  }
  
  console.log(`Showing ${type}s popup`);
  attractionsPopup.classList.remove('hidden');
}

function hideAttractions() {
  console.log('Hiding attractions popup');
  attractionsPopup.classList.add('hidden');
}

// Close popup when clicking outside
function handlePopupClick(event) {
  if (event.target === attractionsPopup) {
    hideAttractions();
  }
}

document.addEventListener("DOMContentLoaded", () => {
  if (video) startCamera();
  
  // Ensure popup starts hidden
  if (attractionsPopup) {
    attractionsPopup.classList.add('hidden');
    console.log('Popup initialized as hidden');
  }
  
  // Add a global function to force hide popup (for debugging)
  window.hideAttractionsPopup = () => {
    if (attractionsPopup) {
      attractionsPopup.classList.add('hidden');
      console.log('Popup force hidden');
    }
  };

  if (scanBtn) {
    scanBtn.addEventListener("click", async () => {
      const dataUrl = captureFrame();
      try {
        const result = await analyzeImage(dataUrl);
        const { landmark, info } = result;
        showOverlay(landmark, info);

        saveBtn.onclick = () => {
          saveToPassport({
            id: Date.now().toString(),
            name: landmark || "Unknown",
            info: info || "",
            image: dataUrl,
            timestamp: new Date().toISOString(),
            toDiscover: false
          });
          hideOverlay();
          alert("Saved to Passport");
        };
      } catch (e) {
        console.error(e);
        alert("Scan failed. Ensure backend is running.");
      }
    });
  }

  if (closeOverlayBtn) {
    closeOverlayBtn.addEventListener("click", () => hideOverlay());
  }

  if (closeAttractionsBtn) {
    closeAttractionsBtn.addEventListener("click", () => hideAttractions());
  }

  if (attractionsPopup) {
    attractionsPopup.addEventListener("click", handlePopupClick);
  }

  // Close popup with Escape key
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && attractionsPopup && !attractionsPopup.classList.contains('hidden')) {
      hideAttractions();
    }
  });

  // Tab switching functionality
  if (attractionsTab && foodTab) {
    attractionsTab.addEventListener('click', () => {
      attractionsTab.classList.add('active');
      foodTab.classList.remove('active');
      attractionsList.classList.remove('hidden');
      foodList.classList.add('hidden');
    });

    foodTab.addEventListener('click', () => {
      foodTab.classList.add('active');
      attractionsTab.classList.remove('active');
      foodList.classList.remove('hidden');
      attractionsList.classList.add('hidden');
    });
  }

  if (findAttractionsBtn) {
    let isRequesting = false;
    let retryTimeout = null;

    const resetButton = () => {
      isRequesting = false;
      findAttractionsBtn.textContent = 'Discover Near Me';
      findAttractionsBtn.disabled = false;
      if (retryTimeout) {
        clearTimeout(retryTimeout);
        retryTimeout = null;
      }
    };

    findAttractionsBtn.addEventListener('click', async () => {
      // Prevent multiple simultaneous requests
      if (isRequesting) {
        console.log('Already processing a request...');
        return;
      }

      try {
        isRequesting = true;
        findAttractionsBtn.textContent = 'Getting Location...';
        findAttractionsBtn.disabled = true;
        
        // Clear any existing error states
        attractionsList.innerHTML = '<p class="loading">Getting your location...</p>';
        foodList.innerHTML = '<p class="loading">Loading...</p>';
        
        // Get location with retry logic
        let location;
        try {
          location = await getCurrentLocation();
          console.log('Location obtained:', location);
        } catch (locationError) {
          console.error('Location error:', locationError);
          throw locationError; // Let the main error handler deal with it
        }
        
        if (!location || !location.lat || !location.lon) {
          throw new Error('Invalid location data received');
        }
        
        findAttractionsBtn.textContent = 'Finding Places...';
        attractionsList.innerHTML = '<p class="loading">Finding places near you...</p>';
        
        // Fetch both attractions and food spots with timeouts
        const fetchWithTimeout = async (promise, name) => {
          const timeout = new Promise((_, reject) => 
            setTimeout(() => reject(new Error(`${name} request timed out`)), 20000)
          );
          return Promise.race([promise, timeout]);
        };

        const [attractionsData, foodData] = await Promise.all([
          fetchWithTimeout(fetchAttractions(location.lat, location.lon)
            .catch(error => {
              console.error('Attractions fetch error:', error);
              return { attractions: [], count: 0 };
            }), 'Attractions'),
          fetchWithTimeout(fetchFoodSpots(location.lat, location.lon)
            .catch(error => {
              console.error('Food spots fetch error:', error);
              return { food_spots: [], food_count: 0 };
            }), 'Food spots')
        ]);

        // Validate responses
        if (!attractionsData || !foodData) {
          throw new Error('Invalid response from server');
        }

        // Display attractions (default tab)
        displayPlaces(attractionsData, 'attraction');
        // Pre-load food data
        displayPlaces(foodData, 'food');
        
        // Show attractions tab by default
        attractionsTab.classList.add('active');
        foodTab.classList.remove('active');
        attractionsList.classList.remove('hidden');
        foodList.classList.add('hidden');
        
      } catch (error) {
        console.error('Error:', error);
        
        // Handle different error types
        let errorMessage;
        if (error.code === 1) {
          errorMessage = 'Please enable location access in your browser settings and try again.';
        } else if (error.code === 2) {
          errorMessage = 'Could not get your location. Please check if location services are enabled on your device.';
        } else if (error.code === 3) {
          errorMessage = 'Location request timed out. Please try again.';
        } else {
          errorMessage = 'Failed to find places: ' + (error.message || 'Unknown error');
        }
        
        alert(errorMessage);
        
        // Clear loading states
        attractionsList.innerHTML = '<p class="error">🚫 ' + errorMessage + '</p>';
        foodList.innerHTML = '';
      } finally {
        resetButton();
      }
    });
  }
});


