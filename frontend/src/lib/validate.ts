export const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp'] as const;
export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

/** Returns an error message, or null if the file is acceptable. */
export function validateImageFile(file: File): string | null {
  if (!(ALLOWED_TYPES as readonly string[]).includes(file.type)) {
    return 'Unsupported file type. Please choose a JPEG, PNG or WebP image.';
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    return 'That image is larger than 10 MB. Please choose a smaller one.';
  }
  if (file.size === 0) {
    return 'That file is empty.';
  }
  return null;
}
