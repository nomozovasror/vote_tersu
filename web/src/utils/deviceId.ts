/**
 * Generate a unique device ID based on browser fingerprint
 * This allows multiple devices on the same WiFi/IP to vote separately
 */

interface DeviceFingerprint {
  userAgent: string;
  language: string;
  platform: string;
  screenResolution: string;
  timezone: number;
  colorDepth: number;
  hardwareConcurrency: number;
  deviceMemory?: number;
  touchSupport: boolean;
}

function getDeviceFingerprint(): DeviceFingerprint {
  const nav = navigator as any;

  return {
    userAgent: navigator.userAgent,
    language: navigator.language,
    platform: navigator.platform,
    screenResolution: `${screen.width}x${screen.height}x${screen.colorDepth}`,
    timezone: new Date().getTimezoneOffset(),
    colorDepth: screen.colorDepth,
    hardwareConcurrency: navigator.hardwareConcurrency || 0,
    deviceMemory: nav.deviceMemory,
    touchSupport: 'ontouchstart' in window || navigator.maxTouchPoints > 0,
  };
}

function hashString(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return Math.abs(hash).toString(36);
}

/**
 * Get or create a persistent device ID
 * Uses localStorage for persistence across sessions
 */
export function getDeviceId(): string {
  const STORAGE_KEY = 'voting_device_id';

  // Try to get existing device ID from localStorage
  let deviceId = localStorage.getItem(STORAGE_KEY);

  if (deviceId) {
    console.log('[DeviceID] Using existing device ID:', deviceId);
    return deviceId;
  }

  // Generate new device ID based on fingerprint
  const fingerprint = getDeviceFingerprint();
  const fingerprintString = JSON.stringify(fingerprint);
  const fingerprintHash = hashString(fingerprintString);

  // Add random component for additional uniqueness
  const randomPart = Math.random().toString(36).substring(2, 10);
  const timestamp = Date.now().toString(36);

  // Combine: timestamp + fingerprint + random
  deviceId = `${timestamp}-${fingerprintHash}-${randomPart}`;

  // Save to localStorage
  localStorage.setItem(STORAGE_KEY, deviceId);

  console.log('[DeviceID] Generated new device ID:', deviceId);
  console.log('[DeviceID] Fingerprint:', fingerprint);

  return deviceId;
}

/**
 * Get device info for debugging
 */
export function getDeviceInfo(): DeviceFingerprint {
  return getDeviceFingerprint();
}

/**
 * Reset device ID (for testing)
 */
export function resetDeviceId(): void {
  localStorage.removeItem('voting_device_id');
  console.log('[DeviceID] Device ID reset');
}
