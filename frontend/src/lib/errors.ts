/** Typed API errors and user-facing copy for them. */

export type ApiErrorKind =
  | 'too_large' // 413
  | 'unsupported_type' // 415
  | 'invalid_image' // 422
  | 'model_unavailable' // 503
  | 'network' // fetch failed / backend unreachable
  | 'aborted' // cancelled by the user
  | 'server' // other HTTP errors
  | 'unknown';

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status?: number;
  readonly detail?: string;
  readonly code?: string;

  constructor(
    kind: ApiErrorKind,
    message: string,
    extra: { status?: number; detail?: string; code?: string } = {},
  ) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind;
    this.status = extra.status;
    this.detail = extra.detail;
    this.code = extra.code;
  }
}

export function kindFromStatus(status: number): ApiErrorKind {
  switch (status) {
    case 413:
      return 'too_large';
    case 415:
      return 'unsupported_type';
    case 422:
      return 'invalid_image';
    case 503:
      return 'model_unavailable';
    default:
      return 'server';
  }
}

export function toApiError(err: unknown): ApiError {
  if (err instanceof ApiError) return err;
  if (err instanceof DOMException && err.name === 'AbortError') {
    return new ApiError('aborted', 'Request cancelled.');
  }
  if (err instanceof TypeError) {
    return new ApiError('network', 'Could not reach the backend.');
  }
  return new ApiError('unknown', err instanceof Error ? err.message : 'Something went wrong.');
}

export interface ErrorCopy {
  title: string;
  message: string;
  /** Whether retrying the same request could plausibly help. */
  retryable: boolean;
}

export function describeApiError(error: ApiError): ErrorCopy {
  switch (error.kind) {
    case 'too_large':
      return {
        title: 'Image is too large',
        message: 'That file is over the 10 MB limit. Try a smaller or compressed photo.',
        retryable: false,
      };
    case 'unsupported_type':
      return {
        title: 'Unsupported file type',
        message: 'Please use a JPEG, PNG or WebP image.',
        retryable: false,
      };
    case 'invalid_image':
      return {
        title: "We couldn't read that image",
        message:
          error.detail ||
          'The file may be corrupted or too small (at least 64 px on the short side). Try another photo.',
        retryable: false,
      };
    case 'model_unavailable':
      return {
        title: 'Model not ready',
        message:
          'The backend is running but the model artifacts are missing. Run the notebooks (python scripts/run_notebooks.py), then retry.',
        retryable: true,
      };
    case 'network':
      return {
        title: 'Backend unreachable',
        message:
          'Could not reach the server. Start it with run_backend.bat (Windows) or ./run_backend.sh (Linux/macOS), then retry.',
        retryable: true,
      };
    case 'aborted':
      return { title: 'Cancelled', message: 'The analysis was cancelled.', retryable: true };
    case 'server':
      return {
        title: 'Server error',
        message: error.detail || 'The server hit an unexpected error. Please try again.',
        retryable: true,
      };
    default:
      return {
        title: 'Something went wrong',
        message: error.message || 'An unexpected error occurred. Please try again.',
        retryable: true,
      };
  }
}
