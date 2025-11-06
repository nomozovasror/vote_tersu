/**
 * Safely copy text to clipboard with fallback for older browsers/HTTP contexts
 * @param text - Text to copy
 * @returns Promise that resolves to true if successful, false otherwise
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  // Try modern clipboard API first (requires HTTPS in production)
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (err) {
      console.warn('Clipboard API failed, falling back to legacy method:', err);
    }
  }

  // Fallback for older browsers or non-secure contexts
  try {
    const textArea = document.createElement('textarea');
    textArea.value = text;

    // Make the textarea invisible and out of viewport
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    textArea.style.opacity = '0';

    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    // Try to copy using execCommand (legacy method)
    const successful = document.execCommand('copy');
    document.body.removeChild(textArea);

    return successful;
  } catch (err) {
    console.error('All clipboard methods failed:', err);
    return false;
  }
}
