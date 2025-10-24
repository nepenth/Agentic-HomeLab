/**
 * Email utility functions for processing and displaying email data.
 */

/**
 * Decode MIME encoded-word syntax (RFC 2047) in email headers.
 * Handles formats like: =?UTF-8?Q?encoded_text?= and =?utf-8?B?base64?=
 *
 * Examples:
 *   "=?UTF-8?Q?=E2=80=9CDirector_of_DevOps=E2=80=9D?="
 *   -> ""Director of DevOps""
 *
 * @param encodedText - The potentially MIME-encoded text
 * @returns Decoded text
 */
export function decodeMimeHeader(encodedText: string): string {
  if (!encodedText) return '';

  try {
    // Pattern: =?charset?encoding?encoded-text?=
    // charset: UTF-8, ISO-8859-1, etc.
    // encoding: Q (Quoted-Printable) or B (Base64)
    const mimePattern = /=\?([^?]+)\?([QB])\?([^?]*)\?=/gi;

    let decoded = encodedText;
    const decodedParts: string[] = [];
    let lastIndex = 0;

    // Reset the regex to start from beginning
    mimePattern.lastIndex = 0;
    let match;

    while ((match = mimePattern.exec(encodedText)) !== null) {
      const [fullMatch, charset, encoding, encodedPart] = match;

      // Add any text before this match
      if (match.index > lastIndex) {
        decodedParts.push(encodedText.substring(lastIndex, match.index));
      }

      let decodedPart = '';

      if (encoding.toUpperCase() === 'Q') {
        // Quoted-Printable encoding - decode to bytes first
        const bytes = decodeQuotedPrintableToBytes(encodedPart);
        // Then decode bytes as UTF-8
        decodedPart = decodeUTF8Bytes(bytes, charset);
      } else if (encoding.toUpperCase() === 'B') {
        // Base64 encoding
        try {
          const binaryString = atob(encodedPart);
          // Convert binary string to byte array
          const bytes = new Uint8Array(binaryString.length);
          for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
          }
          decodedPart = decodeUTF8Bytes(bytes, charset);
        } catch (e) {
          console.warn('Failed to decode base64:', e);
          decodedPart = encodedPart;
        }
      }

      decodedParts.push(decodedPart);
      lastIndex = match.index + fullMatch.length;
    }

    // Add any remaining text after last match
    if (lastIndex < encodedText.length) {
      decodedParts.push(encodedText.substring(lastIndex));
    }

    decoded = decodedParts.length > 0 ? decodedParts.join('') : encodedText;

    // Clean up any remaining underscores used as space replacements in Q encoding
    // But only if we found MIME patterns
    if (mimePattern.test(encodedText)) {
      decoded = decoded.replace(/_/g, ' ');
    }

    return decoded;
  } catch (e) {
    console.warn('Failed to decode MIME header:', e);
    return encodedText;
  }
}

/**
 * Decode Quoted-Printable encoding to byte array.
 * Converts =XX hex sequences to actual byte values.
 */
function decodeQuotedPrintableToBytes(text: string): Uint8Array {
  const bytes: number[] = [];
  let i = 0;

  while (i < text.length) {
    if (text[i] === '=' && i + 2 < text.length) {
      // Decode =XX hex sequence
      const hex = text.substring(i + 1, i + 3);
      bytes.push(parseInt(hex, 16));
      i += 3;
    } else if (text[i] === '_') {
      // Underscore represents space in Q encoding
      bytes.push(32); // ASCII space
      i++;
    } else {
      // Regular character
      bytes.push(text.charCodeAt(i));
      i++;
    }
  }

  return new Uint8Array(bytes);
}

/**
 * Decode byte array as UTF-8 text.
 * Properly handles multi-byte UTF-8 sequences.
 */
function decodeUTF8Bytes(bytes: Uint8Array, charset: string): string {
  try {
    // Use TextDecoder for proper UTF-8 decoding
    const decoder = new TextDecoder(charset.toLowerCase());
    return decoder.decode(bytes);
  } catch (e) {
    // Fallback for unsupported charsets
    console.warn(`Unsupported charset ${charset}, falling back to UTF-8`);
    const decoder = new TextDecoder('utf-8');
    return decoder.decode(bytes);
  }
}

/**
 * Truncate text with ellipsis at specified length.
 */
export function truncateText(text: string, maxLength: number): string {
  if (!text || text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
}

/**
 * Format email address for display.
 */
export function formatEmailAddress(email: string, name?: string): string {
  if (name && name !== email) {
    return `${name} <${email}>`;
  }
  return email;
}
