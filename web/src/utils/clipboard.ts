/**
 * Safely copy text to clipboard with fallback for older browsers/HTTP contexts
 * @param text - Text to copy
 * @returns Promise that resolves to true if successful, false otherwise
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  console.log('[Clipboard] Attempting to copy:', text);
  console.log('[Clipboard] Is secure context:', window.isSecureContext);
  console.log('[Clipboard] Has clipboard API:', !!navigator.clipboard);

  // Try modern clipboard API first (requires HTTPS in production)
  if (navigator.clipboard && window.isSecureContext) {
    try {
      console.log('[Clipboard] Using modern Clipboard API');
      await navigator.clipboard.writeText(text);
      console.log('[Clipboard] ✓ Modern API succeeded');
      return true;
    } catch (err) {
      console.warn('[Clipboard] ✗ Modern API failed, falling back to legacy method:', err);
    }
  } else {
    console.log('[Clipboard] Modern API not available, using fallback');
  }

  // Fallback for older browsers or non-secure contexts
  try {
    console.log('[Clipboard] Using legacy execCommand method');
    const textArea = document.createElement('textarea');
    textArea.value = text;

    // Make the textarea invisible and out of viewport
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    textArea.style.opacity = '0';
    textArea.setAttribute('readonly', '');

    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    // For iOS
    const range = document.createRange();
    range.selectNodeContents(textArea);
    const selection = window.getSelection();
    if (selection) {
      selection.removeAllRanges();
      selection.addRange(range);
    }
    textArea.setSelectionRange(0, 999999);

    // Try to copy using execCommand (legacy method)
    const successful = document.execCommand('copy');
    console.log('[Clipboard] execCommand result:', successful);

    document.body.removeChild(textArea);

    if (successful) {
      console.log('[Clipboard] ✓ Legacy method succeeded');
    } else {
      console.log('[Clipboard] ✗ Legacy method failed');
    }

    return successful;
  } catch (err) {
    console.error('[Clipboard] ✗ All clipboard methods failed:', err);
    return false;
  }
}
